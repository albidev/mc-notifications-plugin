"""Persistent notification store for Mission Control.

The store is deliberately separate from Hermes SessionDB: notifications are a
Mission Control concern and must survive agent/session retention independently.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from .policy import choose_event_kind, classify_job, comparable_event_body, load_policy
except ImportError:  # direct module loading in plugin smoke tests
    from policy import choose_event_kind, classify_job, comparable_event_body, load_policy
_DEFAULT_DB = Path.home() / ".hermes" / "mission-control" / "notifications.db"
_DB_PATH = Path(os.environ.get("MISSION_CONTROL_NOTIFICATIONS_DB", str(_DEFAULT_DB))).expanduser()
_ALLOWED_SEVERITIES = {"info", "success", "warning", "error", "action"}
_MAX_TEXT = 4000
_MAX_BODY = 200_000
_REPORT_NAME_RE = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})_(?P<time>\d{2}-\d{2}-\d{2})\.md$")


def _hermes_root() -> Path:
    return Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))).expanduser()


def _profile_cron_roots() -> list[tuple[str, Path]]:
    root = _hermes_root()
    result: list[tuple[str, Path]] = [("default", root / "cron")]
    profiles = root / "profiles"
    if profiles.is_dir():
        result.extend(
            (path.name, path / "cron")
            for path in sorted(profiles.iterdir())
            if path.is_dir()
        )
    return result


def _parse_report_time(path: Path) -> datetime:
    match = _REPORT_NAME_RE.match(path.name)
    if match:
        try:
            local = datetime.strptime(
                f"{match.group('date')} {match.group('time').replace('-', ':')}",
                "%Y-%m-%d %H:%M:%S",
            )
            return local.astimezone().astimezone(timezone.utc)
        except ValueError:
            pass
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def _archive_response(archive: str) -> Optional[str]:
    """Return only the final cron response, dropping the assembled prompt archive."""
    if "## Response" not in archive:
        return archive
    answer = archive.rpartition("## Response")[2].strip()
    if not answer:
        return None
    lines = [line.strip().upper() for line in answer.splitlines() if line.strip()]
    silence_tokens = {"[SILENT]", "SILENT", "NO_REPLY", "NO REPLY"}
    if answer.upper() in silence_tokens or (lines and (lines[0] in silence_tokens or lines[-1] in silence_tokens)):
        return None
    return answer


def _execution_outcome(cron_root: Path, job_id: str, report_time: datetime) -> tuple[str, Optional[str]]:
    db_path = cron_root / "executions.db"
    if not db_path.exists():
        return "success", None
    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT status, finished_at, error FROM executions WHERE job_id = ? AND finished_at IS NOT NULL",
            (job_id,),
        ).fetchall()
        conn.close()
        candidates = []
        for status, finished_at, error in rows:
            try:
                finished = datetime.fromisoformat(str(finished_at)).astimezone(timezone.utc)
                delta = abs((finished - report_time).total_seconds())
            except (TypeError, ValueError):
                continue
            if delta <= 900:
                candidates.append((delta, status, error))
        if candidates:
            _, status, error = min(candidates, key=lambda row: row[0])
            if status == "failed":
                return "error", error
            if status in {"unknown", "running"}:
                return "warning", error
    except (OSError, sqlite3.Error):
        pass
    return "success", None


def _execution_status_context(cron_root: Path, job_id: str, report_time: datetime) -> tuple[str, Optional[str], Optional[str]]:
    db_path = cron_root / "executions.db"
    if not db_path.exists():
        return "completed", None, None
    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT status, finished_at, error FROM executions WHERE job_id = ? AND finished_at IS NOT NULL",
            (job_id,),
        ).fetchall()
        conn.close()
    except (OSError, sqlite3.Error):
        return "completed", None, None
    parsed = []
    for status, finished_at, error in rows:
        try:
            finished = datetime.fromisoformat(str(finished_at)).astimezone(timezone.utc)
        except (TypeError, ValueError):
            continue
        parsed.append((finished, str(status or "unknown"), error))
    if not parsed:
        return "completed", None, None
    current = min(parsed, key=lambda row: abs((row[0] - report_time).total_seconds()))
    if abs((current[0] - report_time).total_seconds()) > 900:
        return "completed", None, None
    previous = max((row for row in parsed if row[0] < current[0]), default=None, key=lambda row: row[0])
    return current[1], previous[1] if previous else None, current[2]


def _event_notification(
    *,
    profile: str,
    cron_root: Path,
    job: Dict[str, Any],
    policy: Dict[str, Any],
    output_file: Path,
    body: str,
    report_time: datetime,
    previous_body: Optional[str],
) -> Optional[Dict[str, Any]]:
    job_id = str(job.get("id") or "").strip()
    job_name = str(job.get("name") or job_id).strip()
    current_status, previous_status, execution_error = _execution_status_context(cron_root, job_id, report_time)
    current_comparable = comparable_event_body(body)
    previous_comparable = comparable_event_body(previous_body) if previous_body is not None else None
    output_changed = previous_body is not None and bool(current_comparable) and previous_comparable != current_comparable
    event_kind = choose_event_kind(current_status, previous_status, output_changed=output_changed)
    routing = classify_job(job, policy)
    if event_kind is None or event_kind not in routing["on"]:
        return None
    if routing["mode"] == "silent" and event_kind != "failed":
        return None
    severity = {"failed": "error", "recovered": "success", "changed": "info"}[event_kind]
    detail = execution_error or body
    if len(detail) > 2400:
        detail = f"{detail[:1200]}\n\n[… output abbreviato …]\n\n{detail[-1000:]}"
    fingerprint_source = execution_error if event_kind == "failed" and execution_error else body
    fingerprint = hashlib.sha256(f"{event_kind}:{fingerprint_source}".encode("utf-8", errors="replace")).hexdigest()[:20]
    return {
        "dedupeKey": f"cron:{profile}:{job_id}:event:{event_kind}:{fingerprint}",
        "type": "cron.event",
        "severity": severity,
        "title": f"{job_name} · {event_kind}",
        "body": f"**Event:** `{event_kind}`\n\n**Job:** `{job_name}`\n\n**Run:** `{report_time.isoformat()}`\n\n{detail}",
        "source": {"kind": "cron", "id": job_id},
        "profile": profile,
        "deepLink": f"/cron?job={job_id}&profile={profile}",
        "payload": {
            "kind": "cron-event",
            "event": event_kind,
            "jobId": job_id,
            "jobName": job_name,
            "outputFile": str(output_file),
            "executionError": execution_error,
        },
        "_createdAt": report_time.isoformat(),
    }


def _cron_delivery_reports() -> list[Dict[str, Any]]:
    reports: list[Dict[str, Any]] = []
    policy = load_policy()
    for profile, cron_root in _profile_cron_roots():
        jobs_path = cron_root / "jobs.json"
        try:
            jobs_payload = json.loads(jobs_path.read_text(encoding="utf-8"))
            jobs = jobs_payload.get("jobs", []) if isinstance(jobs_payload, dict) else []
        except (OSError, ValueError, TypeError):
            continue
        for job in jobs:
            if not isinstance(job, dict):
                continue
            job_id = str(job.get("id") or "").strip()
            job_name = str(job.get("name") or job_id).strip()
            output_dir = cron_root / "output" / job_id
            if not job_id or not output_dir.is_dir():
                continue
            routing = classify_job(job, policy)
            output_files = sorted(output_dir.glob("*.md"))
            if not output_files:
                continue
            if routing["mode"] == "report":
                for output_file in output_files:
                    try:
                        archive = output_file.read_text(encoding="utf-8", errors="replace").strip()
                    except OSError:
                        continue
                    body = _archive_response(archive)
                    if not body:
                        continue
                    report_time = _parse_report_time(output_file)
                    severity, execution_error = _execution_outcome(cron_root, job_id, report_time)
                    reports.append({
                        "dedupeKey": f"cron:{profile}:{job_id}:delivery:{output_file.name}",
                        "type": "cron.delivery",
                        "severity": severity,
                        "title": f"{job_name} · report",
                        "body": body,
                        "source": {"kind": "cron", "id": job_id},
                        "profile": profile,
                        "deepLink": f"/cron?job={job_id}&profile={profile}",
                        "payload": {
                            "kind": "cron-report",
                            "jobId": job_id,
                            "jobName": job_name,
                            "outputFile": str(output_file),
                            "schedule": job.get("schedule_display") or job.get("schedule"),
                            "executionError": execution_error,
                        },
                        "_createdAt": report_time.isoformat(),
                    })
                continue

            output_file = output_files[-1]
            try:
                archive = output_file.read_text(encoding="utf-8", errors="replace").strip()
            except OSError:
                continue
            body = _archive_response(archive)
            if not body:
                continue
            previous_body = None
            if len(output_files) > 1:
                try:
                    previous_body = _archive_response(output_files[-2].read_text(encoding="utf-8", errors="replace").strip())
                except OSError:
                    previous_body = None
            event = _event_notification(
                profile=profile,
                cron_root=cron_root,
                job=job,
                policy=policy,
                output_file=output_file,
                body=body,
                report_time=_parse_report_time(output_file),
                previous_body=previous_body,
            )
            if event:
                reports.append(event)
    return reports


def _sync_cron_delivery_reports() -> None:
    for report in _cron_delivery_reports():
        publish_notification(report, created_at=report.pop("_createdAt", None))


class NotificationValidationError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id TEXT PRIMARY KEY,
            dedupe_key TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL,
            severity TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT 'system',
            source_id TEXT,
            profile TEXT,
            created_at TEXT NOT NULL,
            read_at TEXT,
            archived_at TEXT,
            deep_link TEXT,
            payload_json TEXT NOT NULL DEFAULT '{}'
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications(created_at DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_notifications_unread ON notifications(read_at, created_at DESC)"
    )
    conn.commit()
    return conn


def _row(row: sqlite3.Row) -> Dict[str, Any]:
    payload = {}
    try:
        payload = json.loads(row["payload_json"] or "{}")
    except (TypeError, ValueError):
        payload = {}
    return {
        "id": row["id"],
        "dedupeKey": row["dedupe_key"],
        "type": row["type"],
        "severity": row["severity"],
        "title": row["title"],
        "body": row["body"],
        "source": {
            "kind": row["source_kind"],
            "id": row["source_id"],
        },
        "profile": row["profile"],
        "createdAt": row["created_at"],
        "readAt": row["read_at"],
        "archivedAt": row["archived_at"],
        "deepLink": row["deep_link"],
        "payload": payload,
    }


def _require_text(body: Dict[str, Any], key: str, *, max_length: int = _MAX_TEXT) -> str:
    value = str(body.get(key) or "").strip()
    if not value:
        raise NotificationValidationError(f"Missing {key}")
    if len(value) > max_length:
        raise NotificationValidationError(f"{key} is too long")
    return value


def publish_notification(body: Dict[str, Any], *, created_at: Optional[str] = None) -> Dict[str, Any]:
    dedupe_key = _require_text(body, "dedupeKey")
    notification_type = _require_text(body, "type", max_length=120)
    severity = str(body.get("severity") or "info").strip().lower()
    if severity not in _ALLOWED_SEVERITIES:
        raise NotificationValidationError("severity must be one of: info, success, warning, error, action")
    title = _require_text(body, "title", max_length=240)
    text = str(body.get("body") or "").strip()
    if len(text) > _MAX_BODY:
        raise NotificationValidationError("body is too long")
    raw_source = body.get("source")
    source: Dict[str, Any] = dict(raw_source) if isinstance(raw_source, dict) else {}
    source_kind = str(source.get("kind") or "system").strip()[:80] or "system"
    source_id = str(source.get("id") or "").strip()[:240] or None
    profile = str(body.get("profile") or "").strip()[:120] or None
    deep_link = str(body.get("deepLink") or "").strip()[:500] or None
    payload = body.get("payload") if isinstance(body.get("payload"), dict) else {}
    created_at = created_at or _now()
    notification_id = uuid.uuid4().hex

    conn = _connect()
    try:
        existing = conn.execute(
            "SELECT * FROM notifications WHERE dedupe_key = ?", (dedupe_key,)
        ).fetchone()
        if existing is not None:
            if notification_type == "cron.delivery" and (
                existing["body"] != text or existing["title"] != title or existing["severity"] != severity
            ):
                conn.execute(
                    """
                    UPDATE notifications
                    SET severity = ?, title = ?, body = ?, created_at = ?,
                        deep_link = ?, payload_json = ?
                    WHERE id = ?
                    """,
                    (
                        severity,
                        title,
                        text,
                        created_at,
                        deep_link,
                        json.dumps(payload, ensure_ascii=False),
                        existing["id"],
                    ),
                )
                conn.commit()
                existing = conn.execute("SELECT * FROM notifications WHERE id = ?", (existing["id"],)).fetchone()
            return _row(existing)
        conn.execute(
            """
            INSERT INTO notifications
              (id, dedupe_key, type, severity, title, body, source_kind,
               source_id, profile, created_at, deep_link, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                notification_id,
                dedupe_key,
                notification_type,
                severity,
                title,
                text,
                source_kind,
                source_id,
                profile,
                created_at,
                deep_link,
                json.dumps(payload, ensure_ascii=False),
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM notifications WHERE id = ?", (notification_id,)).fetchone()
        assert row is not None
        return _row(row)
    finally:
        conn.close()


def list_notifications(
    *,
    limit: int = 50,
    offset: int = 0,
    unread_only: bool = False,
    read_filter: Optional[str] = None,
    search: Optional[str] = None,
    profile: Optional[str] = None,
) -> Dict[str, Any]:
    _sync_cron_delivery_reports()
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))
    read_filter = str(read_filter or "").strip().lower() or None
    if unread_only:
        read_filter = "unread"
    if read_filter not in {None, "unread", "read"}:
        raise ValueError("read_filter must be 'unread' or 'read'")
    clauses = ["archived_at IS NULL"]
    args: list[Any] = []
    if profile:
        clauses.append("profile = ?")
        args.append(profile)
    needle = str(search or "").strip().lower()
    if needle:
        pattern = f"%{needle}%"
        clauses.append(
            "(LOWER(title) LIKE ? OR LOWER(body) LIKE ? OR LOWER(COALESCE(profile, '')) LIKE ? "
            "OR LOWER(COALESCE(source_kind, '')) LIKE ? OR LOWER(COALESCE(source_id, '')) LIKE ?)"
        )
        args.extend([pattern] * 5)
    base_where = " AND ".join(clauses)
    list_clauses = [*clauses]
    list_args = [*args]
    if read_filter == "unread":
        list_clauses.append("read_at IS NULL")
    elif read_filter == "read":
        list_clauses.append("read_at IS NOT NULL")
    list_where = " AND ".join(list_clauses)
    conn = _connect()
    try:
        rows = conn.execute(
            f"SELECT * FROM notifications WHERE {list_where} ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
            (*list_args, limit, offset),
        ).fetchall()
        unread_count = conn.execute(
            f"SELECT COUNT(*) FROM notifications WHERE {base_where} AND read_at IS NULL",
            args,
        ).fetchone()[0]
        read_count = conn.execute(
            f"SELECT COUNT(*) FROM notifications WHERE {base_where} AND read_at IS NOT NULL",
            args,
        ).fetchone()[0]
        all_count = conn.execute(
            f"SELECT COUNT(*) FROM notifications WHERE {base_where}",
            args,
        ).fetchone()[0]
        total = conn.execute(
            f"SELECT COUNT(*) FROM notifications WHERE {list_where}", list_args,
        ).fetchone()[0]
        next_offset = offset + len(rows)
        return {
            "items": [_row(row) for row in rows],
            "unreadCount": int(unread_count),
            "readCount": int(read_count),
            "allCount": int(all_count),
            "total": int(total),
            "hasMore": next_offset < int(total),
            "nextOffset": next_offset if next_offset < int(total) else None,
        }
    finally:
        conn.close()


def mark_notification_read(notification_id: str) -> Optional[Dict[str, Any]]:
    conn = _connect()
    try:
        conn.execute(
            "UPDATE notifications SET read_at = COALESCE(read_at, ?) WHERE id = ?",
            (_now(), notification_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM notifications WHERE id = ?", (notification_id,)).fetchone()
        return _row(row) if row is not None else None
    finally:
        conn.close()


def mark_all_notifications_read(*, profile: Optional[str] = None) -> Dict[str, Any]:
    conn = _connect()
    try:
        if profile:
            cursor = conn.execute(
                "UPDATE notifications SET read_at = COALESCE(read_at, ?) WHERE profile = ? AND read_at IS NULL AND archived_at IS NULL",
                (_now(), profile),
            )
        else:
            cursor = conn.execute(
                "UPDATE notifications SET read_at = COALESCE(read_at, ?) WHERE read_at IS NULL AND archived_at IS NULL",
                (_now(),),
            )
        conn.commit()
        return {"markedRead": int(cursor.rowcount)}
    finally:
        conn.close()
