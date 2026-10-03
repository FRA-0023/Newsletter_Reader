import sqlite3
from pathlib import Path
from typing import Optional
from datetime import datetime
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
                notion_page_id TEXT,
                digest_sent INTEGER DEFAULT 0,
                processed_at TIMESTAMP NOT NULL
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
    ) -> None:
        conn = self._get_connection()
        conn.execute(
            """
            INSERT OR REPLACE INTO processed_emails
            (message_id, domain_id, subject, notion_page_id, digest_sent, processed_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                message_id.strip(),
                domain_id,
                subject,
                notion_page_id,
                1 if digest_sent else 0,
                datetime.utcnow(),
            ),
        )
        conn.commit()
        logger.info(f"Recorded processed message {message_id} for domain '{domain_id}'.")

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
