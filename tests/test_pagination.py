import handlers


def _publish(index: int):
    return handlers.publish_notification({
        "dedupeKey": f"test:{index}",
        "type": "test",
        "title": f"Notification {index}",
        "body": f"Body {index}",
        "source": {"kind": "test", "id": str(index)},
        "profile": "default",
        "createdAt": f"2026-01-01T00:00:{index:02d}+00:00",
    })


def test_notifications_are_returned_in_pages(monkeypatch, tmp_path):
    monkeypatch.setattr(handlers, "_DB_PATH", tmp_path / "notifications.db")
    monkeypatch.setattr(handlers, "_sync_cron_delivery_reports", lambda: None)
    for index in range(5):
        _publish(index)

    first = handlers.list_notifications(limit=2, offset=0)
    second = handlers.list_notifications(limit=2, offset=2)

    assert [item["title"] for item in first["items"]] == ["Notification 4", "Notification 3"]
    assert first["total"] == 5
    assert first["allCount"] == 5
    assert first["hasMore"] is True
    assert first["nextOffset"] == 2
    assert [item["title"] for item in second["items"]] == ["Notification 2", "Notification 1"]
    assert second["hasMore"] is True
    assert second["nextOffset"] == 4


def test_notifications_support_server_side_search_and_read_filter(monkeypatch, tmp_path):
    monkeypatch.setattr(handlers, "_DB_PATH", tmp_path / "notifications.db")
    monkeypatch.setattr(handlers, "_sync_cron_delivery_reports", lambda: None)
    for index in range(3):
        _publish(index)
    handlers.mark_notification_read(handlers.list_notifications(limit=1)["items"][0]["id"])

    result = handlers.list_notifications(limit=10, search="Body 2", read_filter="read")

    assert result["total"] == 1
    assert result["allCount"] == 1
    assert result["items"][0]["title"] == "Notification 2"
    result = handlers.list_notifications(limit=10, search="Body 0", read_filter="unread")
    assert result["total"] == 1
    assert result["items"][0]["title"] == "Notification 0"
