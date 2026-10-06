import sys
import time
import socket
import signal
import logging
import threading
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Callable, Optional, Any
from zoneinfo import ZoneInfo
from croniter import croniter

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import load_yaml_config, EnvSettings, DomainConfig
from src.adapters.sqlite_store import SQLiteStore
from src.adapters.gemini_client import QuotaExhaustedError
from src.core.engine import NewsletterEngine
from src.core.daily_briefing import DailyBriefingService

logger = logging.getLogger("daemon")


def acquire_daemon_lock(lock_file_path: Path):
    """
    Prevents duplicate instances of the daemon from running concurrently on Windows.
    Returns the open file handle if the lock was acquired, or None if another instance is active.
    """
    lock_file_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        f = open(lock_file_path, "w")
        import msvcrt
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        f.write(f"PID: {sys.argv}\nStarted: {datetime.now().isoformat()}\n")
        f.flush()
        return f
    except (OSError, ImportError):
        return None


def release_daemon_lock(lock_handle, lock_file_path: Path) -> None:
    """Safely releases and cleans up the single-instance lock."""
    if lock_handle:
        try:
            import msvcrt
            msvcrt.locking(lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
        except Exception:
            pass
        try:
            lock_handle.close()
        except Exception:
            pass
    try:
        if lock_file_path.exists():
            lock_file_path.unlink(missing_ok=True)
    except Exception:
        pass


def wait_for_network(max_wait_seconds: int = 25, check_host: str = "1.1.1.1", port: int = 443) -> bool:
    """
    Verifies that network/internet connectivity is active on Windows boot.
    Probes HTTPS/TLS ports (443 / 993) to avoid WinError 10013 on restricted raw DNS ports.
    """
    targets = [(check_host, port), ("8.8.8.8", 443), ("imap.gmail.com", 993)]
    start_time = time.time()
    while time.time() - start_time < max_wait_seconds:
        for host, p in targets:
            try:
                s = socket.create_connection((host, p), timeout=2.0)
                s.close()
                logger.info(f"Internet connectivity verified via {host}:{p}.")
                return True
            except (OSError, TimeoutError):
                continue
        logger.debug("Waiting for network connection to become ready...")
        time.sleep(2.0)
    logger.warning(f"Network not verified after {max_wait_seconds}s. Proceeding with best effort.")
    return False


def is_schedule_missed(
    cron_str: str,
    tz_str: str,
    last_run_at: Optional[datetime],
    max_lookback_days: int = 7,
    now: Optional[datetime] = None,
) -> bool:
    """
    Determines if a cron schedule was missed while the computer was powered off or daemon stopped.
    Returns True if:
      - It has never run before and the previous fire time is within max_lookback_days, OR
      - The previous fire time occurred AFTER the last recorded run time.
    """
    try:
        tz = ZoneInfo(tz_str)
    except Exception:
        tz = ZoneInfo("UTC")

    if now is None:
        now_dt = datetime.now(tz)
    else:
        now_dt = now.astimezone(tz) if now.tzinfo else now.replace(tzinfo=tz)

    try:
        c_iter = croniter(cron_str, now_dt)
        prev_fire = c_iter.get_prev(datetime)
    except Exception as e:
        logger.error(f"Failed to calculate previous fire time for cron '{cron_str}': {e}")
        return False

    prev_naive = prev_fire.replace(tzinfo=None)
    now_naive = now_dt.replace(tzinfo=None)

    # Do not catch up if the missed scheduled time is older than the lookback window
    if now_naive - prev_naive > timedelta(days=max_lookback_days):
        return False

    if last_run_at is None:
        return True

    last_naive = last_run_at.replace(tzinfo=None)
    return last_naive < prev_naive


def execute_job_with_retry(
    job_id: str,
    job_name: str,
    job_func: Callable[[], Any],
    store: SQLiteStore,
    scheduler: Optional[BlockingScheduler] = None,
    max_immediate_retries: int = 3,
    initial_delay_sec: float = 10.0,
    delayed_retry_minutes: int = 10,
) -> bool:
    """
    Executes a job with:
    1. Immediate retry with exponential backoff on transient errors (e.g. socket timeout, IMAP disconnect).
    2. Fail-fast shutdown on Gemini QuotaExhaustedError (429).
    3. State recording in SQLite job_executions.
    4. Delayed follow-up retry in APScheduler (+10 mins) if all immediate attempts fail,
       preventing 24-hour skips when internet is down.
    """
    for attempt in range(1, max_immediate_retries + 1):
        try:
            logger.info(f"Executing '{job_name}' (attempt {attempt}/{max_immediate_retries})...")
            job_func()
            store.record_job_execution(job_id, status="success")
            logger.info(f"Job '{job_name}' completed successfully.")

            # Clear any pending fallback retry if scheduled
            if scheduler and scheduler.running:
                retry_job_id = f"retry_{job_id}"
                if scheduler.get_job(retry_job_id):
                    try:
                        scheduler.remove_job(retry_job_id)
                        logger.debug(f"Removed pending retry job '{retry_job_id}'.")
                    except Exception:
                        pass
            return True

        except QuotaExhaustedError as e:
            logger.critical(
                f"[QUOTA FATAL] Gemini API quota completely exhausted during '{job_name}'. "
                f"Shutting down daemon immediately: {e}"
            )
            store.record_job_execution(job_id, status="quota_exhausted", error_message=str(e))
            raise

        except Exception as e:
            logger.warning(f"Attempt {attempt}/{max_immediate_retries} failed for '{job_name}': {e}")
            if attempt < max_immediate_retries:
                delay = initial_delay_sec * (2 ** (attempt - 1))
                logger.info(f"Waiting {delay:.1f}s before next immediate retry...")
                time.sleep(delay)
            else:
                logger.error(f"All {max_immediate_retries} immediate attempts failed for '{job_name}': {e}", exc_info=True)
                store.record_job_execution(job_id, status="failed", error_message=str(e))

                # Schedule delayed retry via APScheduler if scheduler is running
                if scheduler and scheduler.running:
                    retry_time = datetime.now() + timedelta(minutes=delayed_retry_minutes)
                    retry_job_id = f"retry_{job_id}"
                    logger.info(
                        f"Scheduling delayed fallback retry for '{job_name}' at {retry_time.strftime('%H:%M:%S')} (in {delayed_retry_minutes}m)."
                    )
                    scheduler.add_job(
                        lambda: execute_job_with_retry(
                            job_id,
                            job_name,
                            job_func,
                            store,
                            scheduler,
                            max_immediate_retries=2,
                            initial_delay_sec=15.0,
                            delayed_retry_minutes=delayed_retry_minutes,
                        ),
                        trigger="date",
                        run_date=retry_time,
                        id=retry_job_id,
                        name=f"Retry {job_name}",
                        replace_existing=True,
                    )
                return False
    return False


def run_startup_catchup(
    config,
    store: SQLiteStore,
    engine: NewsletterEngine,
    daily_briefing_svc: DailyBriefingService,
    scheduler: BlockingScheduler,
    now: Optional[datetime] = None,
) -> None:
    """
    Audits all enabled domains and daily briefing on daemon startup.
    If a job's scheduled cron time passed while the computer was off, executes catch-up immediately.
    """
    logger.info("=== Running Startup Catch-Up Audit (Checking for missed runs while PC was off) ===")

    current_date = now.date() if now else date.today()

    # 1. Catch up newsletter domains
    for domain in config.domains:
        if not domain.enabled:
            continue

        cron_str = domain.schedule.cron.strip()
        tz_str = domain.schedule.timezone
        last_exec = store.get_last_job_execution(f"domain_{domain.id}")
        last_run_at = last_exec["last_run_at_dt"] if last_exec else None
        last_status = last_exec["status"] if last_exec else None

        missed = is_schedule_missed(cron_str, tz_str, last_run_at, now=now)
        failed_previously = last_status == "failed"

        if missed or failed_previously:
            reason = "failed previously" if failed_previously else "missed scheduled time while PC was off"
            logger.info(f"[CATCH-UP TRIGGERED] Domain [{domain.id}] '{domain.display_name}' ({reason}). Running now...")
            try:
                execute_job_with_retry(
                    job_id=f"domain_{domain.id}",
                    job_name=f"Catch-up {domain.display_name}",
                    job_func=lambda d=domain: engine.process_domain(d),
                    store=store,
                    scheduler=scheduler,
                )
            except QuotaExhaustedError:
                raise
            except Exception as e:
                logger.error(f"Catch-up execution failed for domain '{domain.id}': {e}", exc_info=True)
        else:
            logger.debug(f"[CATCH-UP OK] Domain [{domain.id}] is up to date (last run: {last_run_at}).")

    # 2. Catch up Daily Briefing
    if config.daily_briefing and config.daily_briefing.enabled:
        b_cron = config.daily_briefing.schedule.cron.strip()
        b_tz = config.daily_briefing.schedule.timezone
        today_str = current_date.isoformat()
        yesterday_str = (current_date - timedelta(days=1)).isoformat()

        # Check yesterday: did the PC turn off before yesterday's briefing?
        yesterday_records = store.get_records_by_date(yesterday_str)
        yesterday_briefing = store.get_daily_briefing(yesterday_str)
        if yesterday_records and not yesterday_briefing:
            logger.info(
                f"[CATCH-UP TRIGGERED] Yesterday's Daily Briefing ({yesterday_str}) was missed "
                f"({len(yesterday_records)} unprocessed emails). Generating now..."
            )
            try:
                execute_job_with_retry(
                    job_id=f"daily_briefing_{yesterday_str}",
                    job_name=f"Catch-up Daily Briefing ({yesterday_str})",
                    job_func=lambda: daily_briefing_svc.generate_and_send(target_date=yesterday_str),
                    store=store,
                    scheduler=scheduler,
                )
            except QuotaExhaustedError:
                raise
            except Exception as e:
                logger.error(f"Catch-up failed for yesterday's Daily Briefing: {e}", exc_info=True)

        # Check today: did today's briefing time pass while the PC was off?
        last_exec_b = store.get_last_job_execution("daily_briefing")
        last_run_b = last_exec_b["last_run_at_dt"] if last_exec_b else None
        today_briefing = store.get_daily_briefing(today_str)
        today_records = store.get_records_by_date(today_str)

        # ARCHITETTURA / LOGICA DI CONTROLLO:
        # Per determinare se il briefing di *oggi* è stato perso mentre il PC era spento,
        # verifichiamo che l'orario programmato di oggi (es. 20:00) sia già trascorso (prev_fire_b.date() == current_date).
        # Se sono le 12:00 o le 17:00, l'orario di oggi non è ancora passato: non dobbiamo anticipare
        # il briefing, ma lasciare che scatti regolarmente al suo orario naturale delle 20:00.
        try:
            tz_obj = ZoneInfo(b_tz)
        except Exception:
            tz_obj = ZoneInfo("UTC")
        now_dt = now if now is not None else datetime.now(tz_obj)
        now_dt = now_dt.astimezone(tz_obj) if now_dt.tzinfo else now_dt.replace(tzinfo=tz_obj)

        c_iter_b = croniter(b_cron, now_dt)
        prev_fire_b = c_iter_b.get_prev(datetime)
        today_time_passed = prev_fire_b.date() == current_date

        if not today_briefing and today_records and today_time_passed and is_schedule_missed(b_cron, b_tz, last_run_b, now=now):
            logger.info(
                f"[CATCH-UP TRIGGERED] Today's Daily Briefing ({today_str}) missed its schedule "
                f"({len(today_records)} emails). Generating now..."
            )
            try:
                execute_job_with_retry(
                    job_id="daily_briefing",
                    job_name="Catch-up Today's Daily Briefing",
                    job_func=lambda: daily_briefing_svc.generate_and_send(target_date=today_str),
                    store=store,
                    scheduler=scheduler,
                )
            except QuotaExhaustedError:
                raise
            except Exception as e:
                logger.error(f"Catch-up failed for today's Daily Briefing: {e}", exc_info=True)

    logger.info("=== Startup Catch-Up Audit Complete ===")


def run_daemon_loop() -> int:
    lock_file = PROJECT_ROOT / "data" / "daemon.lock"
    lock_handle = acquire_daemon_lock(lock_file)
    if not lock_handle:
        logger.warning("Another instance of Newsletter_Reader Daemon is already running. Exiting duplicate process.")
        return 0

    logger.info("Initializing Newsletter_Reader Daemon Loop (Single Instance Active)...")
    config = load_yaml_config()
    env = EnvSettings()
    store = SQLiteStore(config.global_.db_path)
    engine = NewsletterEngine(config.global_, env, store)
    daily_briefing_svc = DailyBriefingService(config.global_, env, store, config)

    # Initialize scheduler with misfire_grace_time=None and coalesce=True
    # This guarantees that laptop sleep/wake or temporary system freezes do NOT drop scheduled jobs.
    scheduler = BlockingScheduler(
        job_defaults={
            "coalesce": True,
            "misfire_grace_time": None,
            "max_instances": 1,
        }
    )

    def make_job_handler(domain_cfg: DomainConfig):
        def job():
            logger.info(f"Cron triggered for domain: [{domain_cfg.id}] '{domain_cfg.display_name}'")
            try:
                execute_job_with_retry(
                    job_id=f"domain_{domain_cfg.id}",
                    job_name=f"Process {domain_cfg.display_name}",
                    job_func=lambda: engine.process_domain(domain_cfg),
                    store=store,
                    scheduler=scheduler,
                )
            except QuotaExhaustedError:
                logger.critical("Shutting down daemon due to QuotaExhaustedError.")
                scheduler.shutdown(wait=False)
                store.close()
                release_daemon_lock(lock_handle, lock_file)
                sys.exit(2)
        return job

    registered_jobs = 0
    for domain in config.domains:
        if not domain.enabled:
            logger.info(f"Skipping disabled domain: {domain.id}")
            continue

        cron_str = domain.schedule.cron.strip()
        tz = domain.schedule.timezone

        try:
            trigger = CronTrigger.from_crontab(cron_str, timezone=tz)
            scheduler.add_job(
                make_job_handler(domain),
                trigger=trigger,
                id=f"job_{domain.id}",
                name=f"Process {domain.display_name}",
                replace_existing=True,
            )
            registered_jobs += 1
            logger.info(f"Registered cron [{cron_str}] ({tz}) for domain '{domain.id}'")
        except Exception as e:
            logger.error(f"Failed to parse cron schedule '{cron_str}' for domain '{domain.id}': {e}")

    # Register Daily Briefing Job
    if config.daily_briefing and config.daily_briefing.enabled:
        b_cron = config.daily_briefing.schedule.cron.strip()
        b_tz = config.daily_briefing.schedule.timezone
        try:
            b_trigger = CronTrigger.from_crontab(b_cron, timezone=b_tz)

            def daily_briefing_job():
                logger.info("Cron triggered for Executive Daily Intelligence Briefing")
                try:
                    execute_job_with_retry(
                        job_id="daily_briefing",
                        job_name="Executive Daily Intelligence Briefing",
                        job_func=lambda: daily_briefing_svc.generate_and_send(),
                        store=store,
                        scheduler=scheduler,
                    )
                except QuotaExhaustedError:
                    logger.critical("Shutting down daemon due to QuotaExhaustedError.")
                    scheduler.shutdown(wait=False)
                    store.close()
                    release_daemon_lock(lock_handle, lock_file)
                    sys.exit(2)

            scheduler.add_job(
                daily_briefing_job,
                trigger=b_trigger,
                id="job_daily_briefing",
                name="Executive Daily Intelligence Briefing",
                replace_existing=True,
            )
            registered_jobs += 1
            logger.info(f"Registered Daily Briefing cron [{b_cron}] ({b_tz})")
        except Exception as e:
            logger.error(f"Failed to register Daily Briefing cron '{b_cron}': {e}")

    logger.info(f"Total cron jobs scheduled: {registered_jobs}")

    # Graceful shutdown handler
    def graceful_shutdown(signum, frame):
        logger.info("Shutdown signal received. Shutting down scheduler gracefully...")
        scheduler.shutdown(wait=False)
        store.close()
        release_daemon_lock(lock_handle, lock_file)
        sys.exit(0)

    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    # 1. Wait for network on boot (avoids instantaneous socket crashes if Wi-Fi takes a few seconds)
    wait_for_network(max_wait_seconds=15)

    # 2. Run catch-up audit on startup (evaluates runs missed while the PC was off)
    try:
        run_startup_catchup(config, store, engine, daily_briefing_svc, scheduler)
    except QuotaExhaustedError:
        logger.critical("Shutting down daemon during catch-up due to QuotaExhaustedError.")
        store.close()
        release_daemon_lock(lock_handle, lock_file)
        return 2
    except Exception as e:
        logger.error(f"Unexpected error during startup catch-up: {e}", exc_info=True)

    # 3. Start periodic wakeup heartbeat to neutralize Windows Modern Standby / Sleep timer drift
    stop_heartbeat = threading.Event()

    def heartbeat_worker():
        while not stop_heartbeat.is_set():
            time.sleep(30)
            if scheduler.running:
                try:
                    scheduler.wakeup()
                except Exception:
                    pass

    heartbeat_thread = threading.Thread(
        target=heartbeat_worker, daemon=True, name="StandbyWakeupHeartbeat"
    )
    heartbeat_thread.start()

    # 4. Start scheduler loop
    logger.info("Scheduler started. Running in background...")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        stop_heartbeat.set()
        store.close()
        release_daemon_lock(lock_handle, lock_file)

    return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
    )
    sys.exit(run_daemon_loop())
