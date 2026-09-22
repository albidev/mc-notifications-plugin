import handlers


def test_cron_sync_runs_only_when_output_fingerprint_changes(monkeypatch, tmp_path):
    cron_root = tmp_path / "cron"
    output = cron_root / "output" / "job-1" / "2026-09-22_09-00-00.md"
    output.parent.mkdir(parents=True)
    output.write_text("first")
    monkeypatch.setattr(handlers, "_profile_cron_roots", lambda: [("default", cron_root)])
    calls = []
    monkeypatch.setattr(handlers, "_sync_cron_delivery_reports", lambda: calls.append(True))
    monkeypatch.setattr(handlers, "_CRON_FINGERPRINT", None)

    assert handlers._sync_cron_if_changed() is True
    assert handlers._sync_cron_if_changed() is False
    assert len(calls) == 1

    output.write_text("second")
    assert handlers._sync_cron_if_changed() is True
    assert len(calls) == 2


def test_cron_sync_retries_after_import_failure(monkeypatch, tmp_path):
    cron_root = tmp_path / "cron"
    output = cron_root / "output" / "job-1" / "2026-09-22_09-00-00.md"
    output.parent.mkdir(parents=True)
    output.write_text("first")
    monkeypatch.setattr(handlers, "_profile_cron_roots", lambda: [("default", cron_root)])
    monkeypatch.setattr(handlers, "_CRON_FINGERPRINT", None)
    attempts = iter([RuntimeError("temporary"), None])
    calls = []
    def sync():
        calls.append(True)
        error = next(attempts)
        if error:
            raise error
    monkeypatch.setattr(handlers, "_sync_cron_delivery_reports", sync)

    assert handlers._sync_cron_if_changed() is False
    assert handlers._sync_cron_if_changed() is True
    assert len(calls) == 2
