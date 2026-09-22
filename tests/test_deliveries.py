import handlers


def _publish(monkeypatch, tmp_path):
    monkeypatch.setattr(handlers, "_DB_PATH", tmp_path / "notifications.db")
    return handlers.publish_notification({
        "dedupeKey": "delivery:test",
        "type": "test",
        "title": "Delivery test",
        "body": "body",
    })


def test_published_notification_records_inbox_delivery(monkeypatch, tmp_path):
    notification = _publish(monkeypatch, tmp_path)

    deliveries = handlers.list_notification_deliveries(notification["id"])

    assert len(deliveries) == 1
    assert deliveries[0]["channel"] == "inbox"
    assert deliveries[0]["target"] == "mission-control"
    assert deliveries[0]["status"] == "delivered"
    assert deliveries[0]["attempts"] == 1
    assert deliveries[0]["deliveredAt"] is not None


def test_delivery_claim_fail_retry_and_complete(monkeypatch, tmp_path):
    notification = _publish(monkeypatch, tmp_path)
    queued = handlers.queue_notification_delivery(
        notification["id"], channel="discord", target="channel-1"
    )

    assert queued["status"] == "pending"
    assert queued["attempts"] == 0

    claimed = handlers.claim_due_deliveries(limit=10)
    assert len(claimed) == 1
    assert claimed[0]["id"] == queued["id"]
    assert claimed[0]["status"] == "retrying"
    assert claimed[0]["attempts"] == 1

    failed = handlers.fail_delivery(queued["id"], "webhook timeout", retry_after_seconds=0)
    assert failed["status"] == "retrying"
    assert failed["error"] == "webhook timeout"
    assert failed["nextRetryAt"] is not None

    claimed_again = handlers.claim_due_deliveries(limit=10)
    assert claimed_again[0]["attempts"] == 2
    completed = handlers.complete_delivery(queued["id"])
    assert completed["status"] == "delivered"
    assert completed["error"] is None
    assert completed["deliveredAt"] is not None


def test_delivery_reaches_failed_after_max_attempts(monkeypatch, tmp_path):
    monkeypatch.setenv("MISSION_CONTROL_NOTIFICATIONS_MAX_ATTEMPTS", "2")
    notification = _publish(monkeypatch, tmp_path)
    queued = handlers.queue_notification_delivery(
        notification["id"], channel="discord", target="channel-2"
    )

    handlers.claim_due_deliveries(limit=10)
    handlers.fail_delivery(queued["id"], "first failure", retry_after_seconds=0)
    handlers.claim_due_deliveries(limit=10)
    failed = handlers.fail_delivery(queued["id"], "second failure", retry_after_seconds=0)

    assert failed["status"] == "failed"
    assert failed["attempts"] == 2
    assert failed["nextRetryAt"] is None
