"""Notification routing policy for cron jobs."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict


_DEFAULT_ON = {
    "report": ["completed", "failed"],
    "event": ["failed"],
    "silent": ["failed"],
}
_ALLOWED_MODES = {"report", "event", "silent"}


def load_policy() -> Dict[str, Any]:
    configured = os.environ.get("MISSION_CONTROL_NOTIFICATIONS_POLICY")
    path = Path(configured).expanduser() if configured else Path(__file__).with_name("notification-policy.json")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        payload = {}
    return payload if isinstance(payload, dict) else {}


def classify_job(job: Dict[str, Any], policy: Dict[str, Any]) -> Dict[str, Any]:
    defaults_raw = policy.get("defaults")
    jobs_raw = policy.get("jobs")
    defaults: Dict[str, Any] = defaults_raw if isinstance(defaults_raw, dict) else {}
    jobs: Dict[str, Any] = jobs_raw if isinstance(jobs_raw, dict) else {}
    key = str(job.get("name") or job.get("id") or "").strip()
    configured_job = jobs.get(key)
    configured = configured_job if isinstance(configured_job, dict) else defaults
    configured = configured if isinstance(configured, dict) else {}
    mode = str(configured.get("mode") or "silent").strip().lower()
    if mode not in _ALLOWED_MODES:
        mode = "silent"
    raw_on = configured.get("on")
    on = [str(value).strip().lower() for value in raw_on] if isinstance(raw_on, list) else []
    on = [value for value in on if value in {"completed", "failed", "recovered", "changed"}]
    return {"mode": mode, "on": on or list(_DEFAULT_ON[mode])}


def comparable_event_body(body: str) -> str:
    """Remove per-run cron metadata before comparing event output."""
    stable_lines = []
    for line in str(body or "").splitlines():
        normalized = line.strip().lower()
        if normalized.startswith("# cron job:"):
            continue
        if any(normalized.startswith(prefix) for prefix in ("**job id:**", "**run time:**", "**schedule:**", "**mode:**", "**status:**")):
            continue
        stable_lines.append(line)
    return re.sub(r"\\s+", " ", "\\n".join(stable_lines)).strip()


def choose_event_kind(latest_status: str, previous_status: str | None, *, output_changed: bool) -> str | None:
    latest = str(latest_status or "").strip().lower()
    previous = str(previous_status or "").strip().lower()
    if latest in {"failed", "failure", "error"}:
        return "failed"
    if latest in {"completed", "success", "succeeded"} and previous in {"failed", "failure", "error"}:
        return "recovered"
    if output_changed:
        return "changed"
    return None
