from datetime import datetime, timedelta, timezone

import handlers


def _notification(index: str):
    return {
        "dedupeKey": f"retention:{index}",
        "type": "test",
        "title": f"Retention {index}",
        "body": f"Body {index}",
        "source": {"kind": "test", "id": index},
    }


def test_retention_prunes_old_read_notifications_only(monkeypatch, tmp_path):
    monkeypatch.setattr(handlers, "_DB_PATH", tmp_path / "notifications.db")
    monkeypatch.setattr(handlers, "_drain_cron_notification_outbox", lambda: None)
    monkeypatch.setattr(handlers, "_sync_cron_delivery_reports", lambda: None)

    old_created = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
    old = handlers.publish_notification(_notification("old"), created_at=old_created)
    fresh = handlers.publish_notification(_notification("fresh"))
    handlers.mark_notification_read(old["id"])

    assert handlers.prune_notifications(retention_days=90) == 1
    result = handlers.list_notifications(limit=10)
    assert [item["id"] for item in result["items"]] == [fresh["id"]]


def test_retention_keeps_old_unread_notifications(monkeypatch, tmp_path):
    monkeypatch.setattr(handlers, "_DB_PATH", tmp_path / "notifications.db")
    monkeypatch.setattr(handlers, "_drain_cron_notification_outbox", lambda: None)
    monkeypatch.setattr(handlers, "_sync_cron_delivery_reports", lambda: None)
    old_created = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
    old = handlers.publish_notification(_notification("unread"), created_at=old_created)

    assert handlers.prune_notifications(retention_days=90) == 0
    assert handlers.list_notifications(limit=10)["items"][0]["id"] == old["id"]
