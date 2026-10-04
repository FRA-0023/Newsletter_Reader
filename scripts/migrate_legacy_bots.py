import sqlite3
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("migrator")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TARGET_DB = PROJECT_ROOT / "data" / "state.db"

SOURCES = [
    {
        "domain_id": "world_population",
        "path": Path("C:/Documenti/Bots/World_Population_Newsletter/data/processed_emails.db"),
        "has_notion_id": False,
    },
    {
        "domain_id": "crypto",
        "path": Path("C:/Documenti/Bots/Crypto_Newsletter/data/processed_emails_crypto.db"),
        "has_notion_id": False,
    },
    {
        "domain_id": "mozi_minute",
        "path": PROJECT_ROOT / "data" / "backups" / "mozi_minute" / "processed_emails.db",
        "has_notion_id": True,
    },
]


def run_migration() -> None:
    if not TARGET_DB.exists():
        logger.error(f"Target database not found: {TARGET_DB}")
        return

    dest_conn = sqlite3.connect(TARGET_DB)
    total_migrated = 0

    for src in SOURCES:
        s_path: Path = src["path"]
        domain = src["domain_id"]

        if not s_path.exists():
            logger.warning(f"Source DB for domain '{domain}' not found at: {s_path}. Skipping.")
            continue

        src_conn = sqlite3.connect(s_path)
        cur = src_conn.cursor()

        try:
            if src["has_notion_id"]:
                cur.execute("SELECT message_id, subject, processed_at, notion_page_id FROM processed_emails")
                rows = cur.fetchall()
                for mid, subj, proc_at, nid in rows:
                    res = dest_conn.execute(
                        """
                        INSERT OR IGNORE INTO processed_emails
                        (message_id, domain_id, subject, notion_page_id, digest_sent, processed_at)
                        VALUES (?, ?, ?, ?, 1, ?)
                        """,
                        (mid.strip(), domain, subj, nid, proc_at),
                    )
                    if res.rowcount > 0:
                        total_migrated += 1
            else:
                cur.execute("SELECT message_id, subject, processed_at FROM processed_emails")
                rows = cur.fetchall()
                for mid, subj, proc_at in rows:
                    res = dest_conn.execute(
                        """
                        INSERT OR IGNORE INTO processed_emails
                        (message_id, domain_id, subject, digest_sent, processed_at)
                        VALUES (?, ?, ?, 1, ?)
                        """,
                        (mid.strip(), domain, subj, proc_at),
                    )
                    if res.rowcount > 0:
                        total_migrated += 1

            dest_conn.commit()
            logger.info(f"Successfully processed {len(rows)} records from '{domain}' source DB.")
        except Exception as e:
            logger.error(f"Error migrating from {s_path}: {e}", exc_info=True)
        finally:
            src_conn.close()

    dest_conn.close()
    logger.info(f"=== Migration complete. Newly inserted records: {total_migrated} ===")


if __name__ == "__main__":
    run_migration()
