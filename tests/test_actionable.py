import handlers


def _isolate(monkeypatch, tmp_path):
    monkeypatch.setattr(handlers, "_DB_PATH", tmp_path / "notifications.db")
    monkeypatch.setattr(handlers, "_drain_cron_notification_outbox", lambda: None)
    monkeypatch.setattr(handlers, "_sync_cron_if_changed", lambda: False)


def test_actionable_filter_includes_action_required_payload(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    handlers.publish_notification({
        "dedupeKey": "action:payload",
        "type": "agent.waiting",
        "severity": "info",
        "title": "Approval needed",
        "body": "Approve the command",
        "payload": {"actionRequired": True},
        "deepLink": "/notifications",
    })
    handlers.publish_notification({
        "dedupeKey": "action:normal",
        "type": "agent.info",
        "severity": "info",
        "title": "FYI",
        "body": "Nothing to do",
    })

    result = handlers.list_notifications(actionable_only=True)
    assert result["total"] == 1
    assert result["actionableCount"] == 1
    assert result["items"][0]["title"] == "Approval needed"


def test_actionable_filter_includes_error_and_warning(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    handlers.publish_notification({
        "dedupeKey": "action:error",
        "type": "job.failed",
        "severity": "error",
        "title": "Job failed",
    })
    result = handlers.list_notifications(actionable_only=True)
    assert result["total"] == 1
    assert result["unreadCount"] == 1
