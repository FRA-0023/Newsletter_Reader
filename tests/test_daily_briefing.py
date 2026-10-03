import pytest
from pathlib import Path
from src.core.schemas import DailyBriefingOutput, DomainBriefingEntry, get_schema_for_type
from src.adapters.sqlite_store import SQLiteStore


def test_daily_briefing_schema():
    payload = {
        "executive_title": "Divergenza Macro e Accelerazione Istituzionale",
        "macro_narrative": "La giornata evidenzia una biforcazione tra metriche demografiche in calo strutturale in Europa e una vigorosa riallocazione di capitale verso asset alternativi e modelli operativi scalabili.",
        "domain_breakdowns": [
            {
                "domain_name": "The Crypto Gateway",
                "core_thesis": "Inflow record su ETF spot BTC guidati da desk istituzionali.",
                "key_takeaways": [
                    "+$420M di volumi netti in ingresso.",
                    "Pressione di vendita assorbita su mercati OTC.",
                ],
                "notion_url": "https://notion.so/test-page-1",
            },
            {
                "domain_name": "Tristan Burns Newsletter",
                "core_thesis": "Focalizzazione sul 'Job to be Done' per evitare obsolescenza del software.",
                "key_takeaways": [
                    "Non ottimizzare l'output ma l'outcome decisionale.",
                    "Evitare la trappola del ghiacciaio (Frederic Tudor case).",
                ],
                "notion_url": "https://notion.so/test-page-2",
            }
        ],
        "actionable_priority": "Riallocare il 20% del budget tecnico sui flussi a maggior ritorno decisionale.",
    }
    schema_cls = get_schema_for_type("daily_briefing")
    obj = schema_cls.model_validate(payload)
    assert isinstance(obj, DailyBriefingOutput)
    assert len(obj.domain_breakdowns) == 2
    assert obj.executive_title == "Divergenza Macro e Accelerazione Istituzionale"


def test_sqlite_daily_records(tmp_path: Path):
    db_file = tmp_path / "test_briefing.db"
    store = SQLiteStore(str(db_file))

    # Record 2 items today
    store.record_processed(
        message_id="mid-1",
        domain_id="crypto",
        subject="Crypto Week",
        headline="Record ETF Inflows",
        bullet_1="+$400M inflows",
        bullet_2="OTC absorbing sales",
        bullet_3="Watch $65k level",
        notion_page_id="notion-111",
        digest_sent=True,
    )
    store.record_processed(
        message_id="mid-2",
        domain_id="mozi_minute",
        subject="Mozi Offers",
        headline="10x Value Rule",
        bullet_1="Value 10x price",
        bullet_2="Done-for-you delivery",
        bullet_3="Double prices",
        notion_page_id="notion-222",
        digest_sent=True,
    )

    records = store.get_records_by_date()
    assert len(records) == 2
    assert records[0]["domain_id"] == "crypto"
    assert records[0]["headline"] == "Record ETF Inflows"
    assert records[1]["domain_id"] == "mozi_minute"
    assert records[1]["bullet_1"] == "Value 10x price"

    # Test daily_briefings dedicated table persistence and retrieval
    store.record_daily_briefing(
        date_str="2026-10-03",
        executive_title="Divergenza Macro e Accelerazione",
        macro_narrative="Sintesi panoramica delle dinamiche di giornata.",
        actionable_priority="Testare pricing dinamico domani mattina.",
        domain_count=2,
        raw_json='{"status": "ok"}',
        notion_page_id="notion-page-daily-briefing-123",
    )

    briefing = store.get_daily_briefing("2026-10-03")
    assert briefing is not None
    assert briefing["executive_title"] == "Divergenza Macro e Accelerazione"
    assert briefing["domain_count"] == 2
    assert briefing["notion_page_id"] == "notion-page-daily-briefing-123"

    store.close()
