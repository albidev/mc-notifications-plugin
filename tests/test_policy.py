from policy import classify_job, choose_event_kind, comparable_event_body


def test_full_report_jobs_keep_every_response():
    policy = {
        "defaults": {"mode": "silent"},
        "jobs": {"crossnection-delivery-morning": {"mode": "report"}},
    }

    assert classify_job({"name": "crossnection-delivery-morning"}, policy) == {
        "mode": "report",
        "on": ["completed", "failed"],
    }


def test_event_jobs_emit_only_configured_transitions():
    policy = {
        "defaults": {"mode": "silent"},
        "jobs": {"omlx-watchdog": {"mode": "event", "on": ["failed", "recovered"]}},
    }

    assert classify_job({"name": "omlx-watchdog"}, policy) == {
        "mode": "event",
        "on": ["failed", "recovered"],
    }
    assert choose_event_kind("failed", "completed", output_changed=False) == "failed"
    assert choose_event_kind("completed", "failed", output_changed=False) == "recovered"
    assert choose_event_kind("completed", "completed", output_changed=True) == "changed"




def test_event_comparison_ignores_per_run_metadata():
    first = """# Cron Job: vault-sync\n**Run Time:** 2026-09-21 05:00:34\n**Status:** silent (empty output)\nNo changes."""
    second = """# Cron Job: vault-sync\n**Run Time:** 2026-09-22 05:00:34\n**Status:** silent (empty output)\nNo changes."""

    assert comparable_event_body(first) == comparable_event_body(second)


def test_unconfigured_jobs_are_silent():
    policy = {"defaults": {"mode": "silent"}, "jobs": {}}

    assert classify_job({"name": "world-news-widget"}, policy) == {
        "mode": "silent",
        "on": ["failed"],
    }
