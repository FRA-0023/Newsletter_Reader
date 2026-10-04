import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import MagicMock, patch

from src.adapters.sqlite_store import SQLiteStore
from src.adapters.gemini_client import QuotaExhaustedError
from src.daemon import (
    is_schedule_missed,
    execute_job_with_retry,
    run_startup_catchup,
    acquire_daemon_lock,
    release_daemon_lock,
)


@pytest.fixture
def temp_store(tmp_path):
    db_file = tmp_path / "test_daemon_store.db"
    store = SQLiteStore(str(db_file))
    yield store
    store.close()


def test_is_schedule_missed_scenarios():
    tz = "Europe/Rome"
    # Scenario 1: Scheduled daily at 10:00, now is 11:30, last ran yesterday at 10:00 -> MISSED
    now = datetime(2026, 10, 4, 11, 30, tzinfo=ZoneInfo(tz))
    last_run = datetime(2026, 10, 3, 10, 0)
    assert is_schedule_missed("0 10 * * *", tz, last_run, now=now) is True

    # Scenario 2: Scheduled daily at 10:00, now is 11:30, last ran today at 10:05 -> NOT MISSED
    last_run_today = datetime(2026, 10, 4, 10, 5)
    assert is_schedule_missed("0 10 * * *", tz, last_run_today, now=now) is False

    # Scenario 3: Scheduled daily at 10:00, now is 09:30 (before trigger time), last ran yesterday -> NOT MISSED
    now_early = datetime(2026, 10, 4, 9, 30, tzinfo=ZoneInfo(tz))
    assert is_schedule_missed("0 10 * * *", tz, last_run, now=now_early) is False

    # Scenario 4: First run ever (last_run is None), prev fire time is recent -> MISSED
    assert is_schedule_missed("0 10 * * *", tz, None, now=now) is True

    # Scenario 5: Previous run was > 7 days ago and max_lookback_days=7 -> NOT MISSED (too ancient)
    old_now = datetime(2026, 10, 20, 11, 30, tzinfo=ZoneInfo(tz))
    assert is_schedule_missed("0 10 1 * *", tz, None, max_lookback_days=7, now=old_now) is False


def test_execute_job_with_retry_success(temp_store):
    mock_func = MagicMock()
    success = execute_job_with_retry(
        job_id="test_job",
        job_name="Test Job",
        job_func=mock_func,
        store=temp_store,
        max_immediate_retries=3,
    )
    assert success is True
    assert mock_func.call_count == 1

    last_exec = temp_store.get_last_job_execution("test_job")
    assert last_exec is not None
    assert last_exec["status"] == "success"


def test_execute_job_with_retry_transient_failure_then_success(temp_store):
    attempts = []

    def flaky_func():
        attempts.append(1)
        if len(attempts) < 2:
            raise ConnectionError("Temporary Wi-Fi drop")
        return True

    success = execute_job_with_retry(
        job_id="flaky_job",
        job_name="Flaky Job",
        job_func=flaky_func,
        store=temp_store,
        max_immediate_retries=3,
        initial_delay_sec=0.01,
    )
    assert success is True
    assert len(attempts) == 2

    last_exec = temp_store.get_last_job_execution("flaky_job")
    assert last_exec["status"] == "success"


def test_execute_job_with_retry_all_fail_schedules_delayed_retry(temp_store):
    mock_func = MagicMock(side_effect=TimeoutError("IMAP connection timeout"))
    mock_scheduler = MagicMock()
    mock_scheduler.running = True

    success = execute_job_with_retry(
        job_id="failing_job",
        job_name="Failing Job",
        job_func=mock_func,
        store=temp_store,
        scheduler=mock_scheduler,
        max_immediate_retries=2,
        initial_delay_sec=0.01,
        delayed_retry_minutes=15,
    )
    assert success is False
    assert mock_func.call_count == 2

    last_exec = temp_store.get_last_job_execution("failing_job")
    assert last_exec["status"] == "failed"
    assert "IMAP connection timeout" in last_exec["error_message"]

    # Verify delayed retry was scheduled in APScheduler
    assert mock_scheduler.add_job.called
    call_kwargs = mock_scheduler.add_job.call_args[1]
    assert call_kwargs["id"] == "retry_failing_job"
    assert call_kwargs["trigger"] == "date"


def test_execute_job_with_retry_quota_exhausted_raises(temp_store):
    mock_func = MagicMock(side_effect=QuotaExhaustedError("RESOURCE_EXHAUSTED 429"))

    with pytest.raises(QuotaExhaustedError):
        execute_job_with_retry(
            job_id="quota_job",
            job_name="Quota Job",
            job_func=mock_func,
            store=temp_store,
            max_immediate_retries=3,
        )

    last_exec = temp_store.get_last_job_execution("quota_job")
    assert last_exec["status"] == "quota_exhausted"


def test_run_startup_catchup_triggers_missed_domain(temp_store):
    mock_domain = MagicMock()
    mock_domain.id = "crypto_daily"
    mock_domain.display_name = "Crypto Daily"
    mock_domain.enabled = True
    mock_domain.schedule.cron = "0 10 * * *"
    mock_domain.schedule.timezone = "Europe/Rome"

    mock_config = MagicMock()
    mock_config.domains = [mock_domain]
    mock_config.daily_briefing = None

    mock_engine = MagicMock()
    mock_briefing_svc = MagicMock()
    mock_scheduler = MagicMock()

    fixed_now = datetime(2026, 10, 4, 11, 0, tzinfo=ZoneInfo("Europe/Rome"))
    temp_store.record_job_execution("domain_crypto_daily", status="success", run_at=datetime(2026, 10, 3, 10, 0))

    run_startup_catchup(
        config=mock_config,
        store=temp_store,
        engine=mock_engine,
        daily_briefing_svc=mock_briefing_svc,
        scheduler=mock_scheduler,
        now=fixed_now,
    )

    assert mock_engine.process_domain.called
    assert mock_engine.process_domain.call_args[0][0].id == "crypto_daily"


def test_daemon_lock(tmp_path):
    lock_file = tmp_path / "daemon.lock"
    handle1 = acquire_daemon_lock(lock_file)
    assert handle1 is not None

    # Second acquisition must fail
    handle2 = acquire_daemon_lock(lock_file)
    assert handle2 is None

    # After releasing, acquisition succeeds again
    release_daemon_lock(handle1, lock_file)
    handle3 = acquire_daemon_lock(lock_file)
    assert handle3 is not None
    release_daemon_lock(handle3, lock_file)
