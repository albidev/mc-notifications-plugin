import handlers


def test_recent_notification_queues_webpush_and_worker_completes(monkeypatch, tmp_path):
    monkeypatch.setattr(handlers, "_DB_PATH", tmp_path / "notifications.db")
    monkeypatch.setattr(handlers.webpush, "queue_target", lambda: "broadcast")
    monkeypatch.setattr(handlers.webpush, "send", lambda notification: {"ok": True, "sent": 1})

    notification = handlers.publish_notification({
        "dedupeKey": "push:test",
        "type": "test",
        "severity": "warning",
        "title": "Push test",
        "body": "Needs attention",
        "deepLink": "/notifications",
    })

    deliveries = handlers.list_notification_deliveries(notification["id"])
    assert sorted(item["channel"] for item in deliveries) == ["inbox", "webpush"]
    webpush_delivery = next(item for item in deliveries if item["channel"] == "webpush")
    assert webpush_delivery["status"] == "pending"

    handlers._deliver_due_notifications()
    deliveries = handlers.list_notification_deliveries(notification["id"])
    webpush_delivery = next(item for item in deliveries if item["channel"] == "webpush")
    assert webpush_delivery["status"] == "delivered"


def test_old_backfill_does_not_queue_webpush(monkeypatch, tmp_path):
    monkeypatch.setattr(handlers, "_DB_PATH", tmp_path / "notifications.db")
    monkeypatch.setattr(handlers.webpush, "queue_target", lambda: "broadcast")

    notification = handlers.publish_notification({
        "dedupeKey": "push:old",
        "type": "cron.delivery",
        "title": "Old report",
        "body": "Historical",
    }, created_at="2020-01-01T00:00:00+00:00")

    deliveries = handlers.list_notification_deliveries(notification["id"])
    assert [item["channel"] for item in deliveries] == ["inbox"]


def test_deep_link_is_internal_only(monkeypatch, tmp_path):
    monkeypatch.setattr(handlers, "_DB_PATH", tmp_path / "notifications.db")

    try:
        handlers.publish_notification({
            "dedupeKey": "push:unsafe-link",
            "type": "test",
            "title": "Unsafe",
            "deepLink": "https://example.com/steal",
        })
    except handlers.NotificationValidationError as exc:
        assert "internal path" in str(exc)
    else:
        raise AssertionError("external deep link was accepted")
