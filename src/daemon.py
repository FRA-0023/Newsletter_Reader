import sys
import signal
import logging
from pathlib import Path
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import load_yaml_config, EnvSettings
from src.adapters.sqlite_store import SQLiteStore
from src.core.engine import NewsletterEngine

logger = logging.getLogger("daemon")


def run_daemon_loop() -> int:
    logger.info("Initializing Newsletter_Reader Daemon Loop...")
    config = load_yaml_config()
    env = EnvSettings()
    store = SQLiteStore(config.global_.db_path)
    engine = NewsletterEngine(config.global_, env, store)

    scheduler = BlockingScheduler()

    def make_job_handler(domain_cfg):
        def job():
            logger.info(f"Cron triggered for domain: [{domain_cfg.id}] '{domain_cfg.display_name}'")
            try:
                engine.process_domain(domain_cfg)
            except Exception as e:
                logger.error(f"Error executing job for domain '{domain_cfg.id}': {e}", exc_info=True)
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

    logger.info(f"Total jobs scheduled: {registered_jobs}")

    def graceful_shutdown(signum, frame):
        logger.info("Shutdown signal received. Shutting down scheduler gracefully...")
        scheduler.shutdown(wait=False)
        store.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    logger.info("Scheduler started. Running in background...")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        store.close()

    return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
    )
    sys.exit(run_daemon_loop())
