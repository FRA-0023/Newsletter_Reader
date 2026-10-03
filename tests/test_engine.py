import pytest
from pathlib import Path
from src.adapters.sqlite_store import SQLiteStore


def test_sqlite_store_idempotency(tmp_path: Path):
    db_file = tmp_path / "test_state.db"
    store = SQLiteStore(str(db_file))

    msg_id = "<test-12345@domain.com>"
    assert not store.is_processed(msg_id)

    store.record_processed(
        message_id=msg_id,
        domain_id="crypto",
        subject="Weekly Crypto Digest",
        notion_page_id="notion-uuid-999",
        digest_sent=True,
    )

    assert store.is_processed(msg_id)
    # Check another random id
    assert not store.is_processed("<different-id@domain.com>")

    store.close()
