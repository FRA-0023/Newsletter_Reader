import argparse
import sys
import logging
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import load_yaml_config, EnvSettings
from src.adapters.sqlite_store import SQLiteStore
from src.core.engine import NewsletterEngine
from src.daemon import run_daemon_loop


def setup_logger(level_name: str = "INFO") -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    logging.basicConfig(
        level=getattr(logging, level_name.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def cmd_validate_config(args) -> int:
    setup_logger("INFO")
    logger = logging.getLogger("cli.validate")
    logger.info("Validating configuration...")

    try:
        config = load_yaml_config()
        logger.info(f"Loaded YAML configuration version: {config.version}")
        logger.info(f"Registered domains: {len(config.domains)}")

        for d in config.domains:
            logger.info(f"Checking domain: [{d.id}] '{d.display_name}'")
            # Check prompt template exists
            tmpl_path = PROJECT_ROOT / d.ai.prompt_template
            if not tmpl_path.exists():
                logger.error(f"  [ERROR] Template not found: {tmpl_path}")
                return 1
            logger.info(f"  [OK] Template found: {d.ai.prompt_template}")
            logger.info(f"  [OK] Schedule: {d.schedule.cron} ({d.schedule.timezone})")
            logger.info(f"  [OK] Filter: {d.filter.sender}")
            logger.info(f"  [OK] Schema: {d.ai.schema_type}")

        logger.info("All configuration checks PASSED successfully.")
        return 0
    except Exception as e:
        logger.critical(f"Configuration validation failed: {e}", exc_info=True)
        return 1


def cmd_run(args) -> int:
    env = EnvSettings()
    setup_logger(env.LOG_LEVEL)
    logger = logging.getLogger("cli.run")

    config = load_yaml_config()
    store = SQLiteStore(config.global_.db_path)
    engine = NewsletterEngine(config.global_, env, store)

    target_domains = []
    if args.domain:
        matched = [d for d in config.domains if d.id == args.domain]
        if not matched:
            logger.error(f"Domain '{args.domain}' not found in configuration.")
            store.close()
            return 1
        target_domains = matched
    else:
        target_domains = [d for d in config.domains if d.enabled]

    total_processed = 0
    try:
        for d in target_domains:
            count = engine.process_domain(d, dry_run=args.dry_run)
            total_processed += count
        logger.info(f"Run completed. Total emails processed: {total_processed}")
        return 0
    finally:
        store.close()


def cmd_daemon(args) -> int:
    env = EnvSettings()
    setup_logger(env.LOG_LEVEL)
    return run_daemon_loop()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Newsletter_Reader: Unified Headless Newsletter Processing Engine"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # validate-config
    sub_val = subparsers.add_parser("validate-config", help="Validate domains.yaml and templates")
    sub_val.set_defaults(func=cmd_validate_config)

    # run
    sub_run = subparsers.add_parser("run", help="Run domain processing")
    sub_run.add_argument("--domain", "-d", help="ID of domain to process (e.g. crypto, world_population)")
    sub_run.add_argument("--dry-run", action="store_true", help="Execute without Notion write or Gmail flag")
    sub_run.set_defaults(func=cmd_run)

    # daemon
    sub_daemon = subparsers.add_parser("daemon", help="Run persistent APScheduler daemon")
    sub_daemon.set_defaults(func=cmd_daemon)

    args = parser.parse_args()
    exit_code = args.func(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
