import sqlite3
from datetime import datetime, timezone

import handlers


def _isolate(monkeypatch, tmp_path):
    hermes = tmp_path / "hermes"
    hermes.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(hermes))
    monkeypatch.setattr(handlers, "_DB_PATH", tmp_path / "notifications.db")
    monkeypatch.setattr(handlers, "_drain_cron_notification_outbox", lambda: None)
    monkeypatch.setattr(handlers, "_sync_cron_if_changed", lambda: False)
    return hermes


def _state_db(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE sessions (id TEXT PRIMARY KEY, source TEXT NOT NULL, title TEXT,"
        " started_at REAL NOT NULL, ended_at REAL, message_count INTEGER DEFAULT 0)"
    )
    conn.executemany(
        "INSERT INTO sessions (id, source, title, started_at, ended_at, message_count) VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()


def _local_ts(stamp: str) -> float:
    return datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S").astimezone().timestamp()


def _cron_notification(job_id, job_name, output_name, *, profile="default", kind="cron"):
    return handlers.publish_notification({
        "dedupeKey": f"cron:{profile}:{job_id}:delivery:{output_name}",
        "type": "cron.delivery",
        "severity": "success",
        "title": f"{job_name} · report",
        "body": "report",
        "source": {"kind": kind, "id": job_id},
        "profile": profile,
        "payload": {
            "kind": "cron-report",
            "jobId": job_id,
            "jobName": job_name,
            "outputFile": f"/tmp/cron/output/{job_id}/{output_name}",
        },
    })


def test_scheduled_run_resolves_by_cron_session_id(monkeypatch, tmp_path):
    hermes = _isolate(monkeypatch, tmp_path)
    _state_db(hermes / "state.db", [
        ("cron_13e9f2fe308d_20261016_075041", "cron", "signal-news · Oct 16 07:52",
         _local_ts("2026-10-16 07:50:41"), _local_ts("2026-10-16 07:52:45"), 25),
        ("cron_13e9f2fe308d_20261017_075041", "cron", "signal-news · Oct 17 07:54",
         _local_ts("2026-10-17 07:50:41"), _local_ts("2026-10-17 07:54:58"), 37),
    ])
    notification = _cron_notification("13e9f2fe308d", "signal-news", "2026-10-17_07-54-58.md")

    result = handlers.resolve_cron_session(notification["id"])

    assert result == {
        "available": True,
        "sessionId": "cron_13e9f2fe308d_20261017_075041",
        "profile": "default",
        "title": "signal-news · Oct 17 07:54",
        "messageCount": 37,
    }


def test_manual_run_resolves_by_title_prefix(monkeypatch, tmp_path):
    hermes = _isolate(monkeypatch, tmp_path)
    _state_db(hermes / "state.db", [
        ("local-failed", "cron", "ops-daily-note · Oct 17 16:30",
         _local_ts("2026-10-17 16:29:51"), _local_ts("2026-10-17 16:30:02"), 2),
        ("local-ok", "cron", "ops-daily-note · Oct 17 16:33",
         _local_ts("2026-10-17 16:30:23"), _local_ts("2026-10-17 16:33:55"), 80),
        ("local-chat", "tui", "ops-daily-note · Oct 17 16:33 chat",
         _local_ts("2026-10-17 16:30:23"), _local_ts("2026-10-17 16:33:56"), 3),
    ])
    ok = _cron_notification("a4f8f371b755", "ops-daily-note", "2026-10-17_16-33-57.md")
    failed = _cron_notification("a4f8f371b755", "ops-daily-note", "2026-10-17_16-30-03.md")

    assert handlers.resolve_cron_session(ok["id"])["sessionId"] == "local-ok"
    assert handlers.resolve_cron_session(failed["id"])["sessionId"] == "local-failed"


def test_script_only_job_has_no_session(monkeypatch, tmp_path):
    hermes = _isolate(monkeypatch, tmp_path)
    _state_db(hermes / "state.db", [
        ("cron_other_20261017_064000", "cron", "signal-news · Oct 17 06:40",
         _local_ts("2026-10-17 06:40:00"), _local_ts("2026-10-17 06:40:30"), 9),
    ])
    notification = _cron_notification("ab12cd34ef56", "state-db-integrity-check", "2026-10-17_06-40-31.md")

    assert handlers.resolve_cron_session(notification["id"]) == {"available": False, "reason": "no_agent_session"}


def test_run_outside_match_window_is_not_attached(monkeypatch, tmp_path):
    hermes = _isolate(monkeypatch, tmp_path)
    _state_db(hermes / "state.db", [
        ("cron_13e9f2fe308d_20261017_050000", "cron", "signal-news · Oct 17 05:01",
         _local_ts("2026-10-17 05:00:00"), _local_ts("2026-10-17 05:01:00"), 9),
    ])
    notification = _cron_notification("13e9f2fe308d", "signal-news", "2026-10-17_07-54-58.md")

    assert handlers.resolve_cron_session(notification["id"])["available"] is False


def test_profile_job_reads_profile_state_db(monkeypatch, tmp_path):
    hermes = _isolate(monkeypatch, tmp_path)
    _state_db(hermes / "state.db", [])
    _state_db(hermes / "profiles" / "crossnection" / "state.db", [
        ("cron_deadbeef0001_20261017_073000", "cron", "crossnection-delivery-morning · Oct 17 07:32",
         _local_ts("2026-10-17 07:30:00"), _local_ts("2026-10-17 07:32:10"), 14),
    ])
    notification = _cron_notification(
        "deadbeef0001", "crossnection-delivery-morning", "2026-10-17_07-32-11.md", profile="crossnection",
    )

    result = handlers.resolve_cron_session(notification["id"])

    assert result["available"] is True
    assert result["profile"] == "crossnection"
    assert result["sessionId"] == "cron_deadbeef0001_20261017_073000"


def test_non_cron_and_unknown_notifications_are_unavailable(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    other = handlers.publish_notification({
        "dedupeKey": "agent:1", "type": "agent.info", "severity": "info", "title": "FYI", "body": "x",
    })

    assert handlers.resolve_cron_session(other["id"]) == {"available": False, "reason": "not_cron"}
    assert handlers.resolve_cron_session("missing") == {"available": False, "reason": "not_found"}


def test_missing_profile_state_db_is_unavailable(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    notification = _cron_notification("13e9f2fe308d", "signal-news", "2026-10-17_07-54-58.md", profile="ghost")

    assert handlers.resolve_cron_session(notification["id"]) == {"available": False, "reason": "no_session_db"}


def test_session_db_is_opened_read_only(monkeypatch, tmp_path):
    hermes = _isolate(monkeypatch, tmp_path)
    _state_db(hermes / "state.db", [
        ("cron_13e9f2fe308d_20261017_075041", "cron", "signal-news · Oct 17 07:54",
         _local_ts("2026-10-17 07:50:41"), _local_ts("2026-10-17 07:54:58"), 37),
    ])
    before = (hermes / "state.db").read_bytes()
    notification = _cron_notification("13e9f2fe308d", "signal-news", "2026-10-17_07-54-58.md")

    handlers.resolve_cron_session(notification["id"])

    assert (hermes / "state.db").read_bytes() == before
    assert not (hermes / "state.db-wal").exists()
