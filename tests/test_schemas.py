import pytest
from src.core.schemas import (
    ExecutiveDigest,
    QuantitativeMetricsPayload,
    QuantitativeExtractionOutput,
    EditorialSection,
    JournalisticEditorialPayload,
    EditorialExtractionOutput,
    BusinessFrameworkPayload,
    FrameworkTableEntry,
    FrameworkExtractionOutput,
    get_schema_for_type,
)


def test_quantitative_schema():
    payload = {
        "digest": {
            "headline": "Crollo Natalità UE a 1.4 Figli per Donna",
            "bullet_1": "Dati: Indice di fecondità medio sceso a 1.46 nell'UE, con Italia a 1.20.",
            "bullet_2": "Dinamica: Impatto su sistema pensionistico e spesa sanitaria entro il 2035.",
            "bullet_3": "Takeaway: Necessità di incentivazione fiscale e attrazione talenti esteri.",
        },
        "notion_data": {
            "macro_topic": "EU Demographics",
            "data_points": [
                "Tasso di fecondità UE pari a 1.46 nel 2025.",
                "Popolazione attiva in calo del 4.2% nei prossimi 10 anni.",
            ],
        },
    }
    model_cls = get_schema_for_type("quantitative_metrics")
    obj = model_cls.model_validate(payload)
    assert isinstance(obj, QuantitativeExtractionOutput)
    assert obj.digest.headline == "Crollo Natalità UE a 1.4 Figli per Donna"
    assert len(obj.notion_data.data_points) == 2


def test_crypto_editorial_schema():
    payload = {
        "digest": {
            "headline": "Inflow ETF Record e Accumulo Istituzionale",
            "bullet_1": "Dati: +$420M di afflussi netti su ETF spot BTC in 48 ore.",
            "bullet_2": "Dinamica: Liquidità assorbita dai desk OTC senza impatto immediato a mercato.",
            "bullet_3": "Takeaway: Rischio short squeeze sopra resistenza dei $65.000.",
        },
        "notion_data": {
            "headline": "Rally Istituzionale e Liquidità OTC ai Massimi",
            "section_whale": {
                "title": "Whale Moves 🐋",
                "body_lines": [
                    "Grandi acquisti registrati dai wallet di custodia BlackRock.",
                    "Miners riducono le vendite del 15% rispetto alla scorsa settimana.",
                ],
            },
            "section_focus": {
                "title": "Focus On: ETF Dynamics 🔎",
                "body_lines": ["La correlazione con i bond decennali si è interrotta."],
            },
            "section_technical": {
                "title": "Analisi Tecnica 📈",
                "body_lines": ["Il supporto a $60.000 ha retto con volumi in espansione."],
            },
            "bottom_line": [
                "La struttura tecnica rimane rialzista sul grafico settimanale.",
                "Mantenere esposizione spot senza leva eccessiva.",
            ],
        },
    }
    model_cls = get_schema_for_type("journalistic_editorial")
    obj = model_cls.model_validate(payload)
    assert isinstance(obj, EditorialExtractionOutput)
    assert obj.notion_data.section_whale.title == "Whale Moves 🐋"


def test_mozi_framework_schema():
    payload = {
        "digest": {
            "headline": "La Regola del 10x Price-to-Value nelle Offerte",
            "bullet_1": "Principio: Se il valore percepito è 10x il prezzo, il prezzo diventa irrilevante.",
            "bullet_2": "Meccanica: Scomporre il delivery in moduli ad alto margine e zero attrito.",
            "bullet_3": "Azione: Raddoppiare il prezzo sul 20% dei clienti top per testare elasticità.",
        },
        "notion_data": {
            "punchy_title": "Come Vendere a 10x Senza Resistenze",
            "intro": "La maggior parte dei business compete sul prezzo perché non sa costruire un'offerta.",
            "core_principle": "Il valore non dipende dal costo di erogazione ma dal risultato ottenuto.",
            "framework_steps": [
                "1. Identifica il dolore più costoso del target.",
                "2. Costruisci la soluzione 'done-for-you'.",
            ],
            "strategy_table": [
                {
                    "scenario": "Clienti che chiedono sconti",
                    "strategic_move": "Aumentare il valore percepito con garanzia o bonus, mai scendere di prezzo",
                }
            ],
            "case_lesson": "Gym Launch ha triplicato i margini rimuovendo i contratti mensili standard.",
            "bottom_line": "Fai offerte così vantaggiose che le persone si sentano stupide a rifiutare.",
        },
    }
    model_cls = get_schema_for_type("business_framework")
    obj = model_cls.model_validate(payload)
    assert isinstance(obj, FrameworkExtractionOutput)
    assert len(obj.notion_data.strategy_table) == 1
