import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


class SQLiteStore:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self) -> None:
        conn = self._get_connection()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_emails (
                message_id TEXT PRIMARY KEY,
                domain_id TEXT NOT NULL,
                subject TEXT,
                headline TEXT,
                bullet_1 TEXT,
                bullet_2 TEXT,
                bullet_3 TEXT,
                notion_page_id TEXT,
                digest_sent INTEGER DEFAULT 0,
                processed_at TIMESTAMP NOT NULL
            )
            """
        )
        # Migration: ensure newly added columns exist if table was already created
        columns = [row[1] for row in conn.execute("PRAGMA table_info(processed_emails)").fetchall()]
        for col in ["headline", "bullet_1", "bullet_2", "bullet_3"]:
            if col not in columns:
                try:
                    conn.execute(f"ALTER TABLE processed_emails ADD COLUMN {col} TEXT")
                except Exception:
                    pass

        # Audit & historical storage for cumulative daily briefings.
        # Decouples email delivery from knowledge persistence, ensuring that even if SMTP fails
        # or Notion sync drops, the synthesized intelligence snapshot for that date is permanently preserved.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_briefings (
                date TEXT PRIMARY KEY,
                executive_title TEXT NOT NULL,
                macro_narrative TEXT NOT NULL,
                actionable_priority TEXT NOT NULL,
                domain_count INTEGER DEFAULT 0,
                raw_json TEXT NOT NULL,
                notion_page_id TEXT,
                created_at TIMESTAMP NOT NULL
            )
            """
        )

        conn.commit()
        logger.debug(f"SQLiteStore initialized at: {self.db_path}")

    def is_processed(self, message_id: str) -> bool:
        if not message_id:
            return False
        conn = self._get_connection()
        cur = conn.execute(
            "SELECT 1 FROM processed_emails WHERE message_id = ?",
            (message_id.strip(),),
        )
        return cur.fetchone() is not None

    def record_processed(
        self,
        message_id: str,
        domain_id: str,
        subject: str,
        notion_page_id: Optional[str] = None,
        digest_sent: bool = False,
        headline: Optional[str] = None,
        bullet_1: Optional[str] = None,
        bullet_2: Optional[str] = None,
        bullet_3: Optional[str] = None,
    ) -> None:
        conn = self._get_connection()
        conn.execute(
            """
            INSERT OR REPLACE INTO processed_emails
            (message_id, domain_id, subject, headline, bullet_1, bullet_2, bullet_3, notion_page_id, digest_sent, processed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message_id.strip(),
                domain_id,
                subject,
                headline,
                bullet_1,
                bullet_2,
                bullet_3,
                notion_page_id,
                1 if digest_sent else 0,
                datetime.utcnow(),
            ),
        )
        conn.commit()
        logger.info(f"Recorded processed message {message_id} for domain '{domain_id}'.")

    def get_records_by_date(self, target_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieves all emails processed on a specific calendar date (UTC/local ISO format YYYY-MM-DD).
        If target_date is omitted, defaults to today's date.
        """
        if target_date is None:
            target_date = date.today().isoformat()

        conn = self._get_connection()
        cur = conn.execute(
            """
            SELECT message_id, domain_id, subject, headline, bullet_1, bullet_2, bullet_3, notion_page_id, digest_sent, processed_at
            FROM processed_emails
            WHERE date(processed_at) = date(?)
            ORDER BY processed_at ASC
            """,
            (target_date,),
        )
        rows = cur.fetchall()
        return [dict(row) for row in rows]

    def record_daily_briefing(
        self,
        date_str: str,
        executive_title: str,
        macro_narrative: str,
        actionable_priority: str,
        domain_count: int,
        raw_json: str,
        notion_page_id: Optional[str] = None,
    ) -> None:
        """
        Stores or updates the daily executive briefing record for a calendar day.
        Using INSERT OR REPLACE ensures idempotency if an operator re-triggers daily-briefing on the same day.
        """
        conn = self._get_connection()
        conn.execute(
            """
            INSERT OR REPLACE INTO daily_briefings
            (date, executive_title, macro_narrative, actionable_priority, domain_count, raw_json, notion_page_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                date_str,
                executive_title,
                macro_narrative,
                actionable_priority,
                domain_count,
                raw_json,
                notion_page_id,
                datetime.utcnow(),
            ),
        )
        conn.commit()
        logger.info(f"Recorded daily briefing for '{date_str}' (domains: {domain_count}) into SQLite state store.")

    def get_daily_briefing(self, date_str: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the consolidated daily briefing record for a specific date if already generated.
        """
        conn = self._get_connection()
        cur = conn.execute(
            """
            SELECT date, executive_title, macro_narrative, actionable_priority, domain_count, raw_json, notion_page_id, created_at
            FROM daily_briefings
            WHERE date = ?
            """,
            (date_str,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
