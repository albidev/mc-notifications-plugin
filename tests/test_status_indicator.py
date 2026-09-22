import handlers


def test_notification_status_is_host_agnostic(monkeypatch, tmp_path):
    monkeypatch.setattr(handlers, "_DB_PATH", tmp_path / "notifications.db")
    monkeypatch.setattr(handlers, "_drain_cron_notification_outbox", lambda: None)
    monkeypatch.setattr(handlers, "_sync_cron_if_changed", lambda: False)
    handlers.publish_notification({
        "dedupeKey": "status:unread",
        "type": "test",
        "severity": "warning",
        "title": "Needs attention",
    })

    status = handlers.notification_status()
    assert status["active"] is True
    assert status["count"] == 1
    assert status["actionableCount"] == 1
    assert status["tone"] == "warning"
    assert status["label"] == "1 unread notification"
