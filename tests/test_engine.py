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


def test_email_notifier_cleaner():
    from src.adapters.email_notifier import _clean_html_markdown, _clean_plain_text

    raw_bullet = "**Principio:** Il valore non dipende dal costo"
    html_cleaned = _clean_html_markdown(raw_bullet)
    assert '<strong style="color: #0f172a; font-weight: 700;">Principio:</strong>' in html_cleaned
    assert not html_cleaned.startswith("*Principio:**")

    plain_cleaned = _clean_plain_text("•*Principio:** Il valore")
    assert plain_cleaned == "**Principio:** Il valore"


def test_language_resolution_cascade():
    from config.settings import resolve_language

    assert resolve_language("it", "en") == "it"
    assert resolve_language(None, "it") == "it"
    assert resolve_language("", "it") == "it"
    assert resolve_language(None, None) == "en"
    assert resolve_language("", "") == "en"
    assert resolve_language("ES", "it") == "es"

