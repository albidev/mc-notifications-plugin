import json

import handlers


def _write_event(root, *, job, execution_id, status="completed", output_file=None, error=None):
    outbox = root / "cron" / "notification-outbox"
    outbox.mkdir(parents=True)
    path = outbox / f"{execution_id}.json"
    path.write_text(json.dumps({
        "schema": 1,
        "event": "cron.completed",
        "eventId": execution_id,
        "createdAt": "2026-09-22T09:00:00+00:00",
        "status": status,
        "error": error,
        "outputFile": str(output_file) if output_file else None,
        "job": job,
    }))
    return path


def test_outbox_report_is_persisted_and_consumed(monkeypatch, tmp_path):
    monkeypatch.setattr(handlers, "_DB_PATH", tmp_path / "notifications.db")
    monkeypatch.setattr(handlers, "_hermes_root", lambda: tmp_path)
    monkeypatch.setattr(handlers, "load_policy", lambda: {
        "defaults": {"mode": "silent", "on": ["failed"]},
        "jobs": {"daily report": {"mode": "report", "on": ["completed", "failed"]}},
    })
    monkeypatch.setattr(handlers, "_sync_cron_delivery_reports", lambda: None)

    output = tmp_path / "cron" / "output" / "job-1" / "2026-09-22_09-00-00.md"
    output.parent.mkdir(parents=True)
    output.write_text("# Prompt\n\n## Response\n\n# Daily report\n\n- done")
    event_path = _write_event(
        tmp_path,
        job={"id": "job-1", "name": "daily report"},
        execution_id="exec-1",
        output_file=output,
    )

    result = handlers.list_notifications(limit=10)

    assert result["total"] == 1
    assert result["items"][0]["type"] == "cron.delivery"
    assert result["items"][0]["body"] == "# Daily report\n\n- done"
    assert not event_path.exists()


def test_outbox_failure_is_published_for_silent_policy(monkeypatch, tmp_path):
    monkeypatch.setattr(handlers, "_DB_PATH", tmp_path / "notifications.db")
    monkeypatch.setattr(handlers, "_hermes_root", lambda: tmp_path)
    monkeypatch.setattr(handlers, "load_policy", lambda: {
        "defaults": {"mode": "silent", "on": ["failed"]},
    })
    monkeypatch.setattr(handlers, "_sync_cron_delivery_reports", lambda: None)

    _write_event(
        tmp_path,
        job={"id": "watchdog", "name": "watchdog"},
        execution_id="exec-failed",
        status="failed",
        error="service is down",
    )

    result = handlers.list_notifications(limit=10)

    assert result["total"] == 1
    item = result["items"][0]
    assert item["type"] == "cron.event"
    assert item["severity"] == "error"
    assert "service is down" in item["body"]
