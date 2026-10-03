from typing import List, Optional, Dict, Type
from pydantic import BaseModel, Field


# ─── CANALE PUSH: EXECUTIVE EMAIL DIGEST (MASSIMO 3 BULLET POINT) ───
class ExecutiveDigest(BaseModel):
    headline: str = Field(
        description="Sintesi telegrafica e incisiva dell'argomento principale (max 10 parole)."
    )
    bullet_1: str = Field(
        description="Punto 1: Il dato quantitativo primario, statistica o metrica verificabile."
    )
    bullet_2: str = Field(
        description="Punto 2: La dinamica di mercato, causa sistemica o fattore determinante."
    )
    bullet_3: str = Field(
        description="Punto 3: L'azione operativa, setup tattico o takeaway strategico."
    )


# ─── CANALE STORAGE: STRUTTURA WORLD POPULATION ─────────────────────
class QuantitativeMetricsPayload(BaseModel):
    macro_topic: str = Field(
        description="Classificazione sintetica in 1-3 parole (es. EU Demographics, US Inflation)."
    )
    data_points: List[str] = Field(
        description="Elenco di 3-8 metriche o evidenze quantitative numeriche con contesto."
    )


class QuantitativeExtractionOutput(BaseModel):
    digest: ExecutiveDigest
    notion_data: QuantitativeMetricsPayload


# ─── CANALE STORAGE: STRUTTURA CRYPTO GATEWAY ────────────────────────
class EditorialSection(BaseModel):
    title: str = Field(description="Titolo della sezione comprensivo di eventuale emoji.")
    body_lines: List[str] = Field(
        description="Frasi distinte della sezione, una frase per elemento."
    )


class JournalisticEditorialPayload(BaseModel):
    headline: str = Field(
        description="Titolo di prima pagina specifico per l'edizione (max 10 parole, italiano)."
    )
    section_whale: EditorialSection = Field(
        description="Sezione Whale Weekend News (emoji 🐋 inclusa)."
    )
    section_focus: EditorialSection = Field(
        description="Sezione Focus on (emoji 🔎 inclusa)."
    )
    section_technical: EditorialSection = Field(
        description="Sezione Analisi tecnica (emoji 📈 inclusa)."
    )
    bottom_line: List[str] = Field(
        description="3-4 frasi di insight editoriale di chiusura."
    )


class EditorialExtractionOutput(BaseModel):
    digest: ExecutiveDigest
    notion_data: JournalisticEditorialPayload


# ─── CANALE STORAGE: STRUTTURA MOZI MINUTE ──────────────────────────
class FrameworkTableEntry(BaseModel):
    scenario: str = Field(description="Scenario di business o problema specifico.")
    strategic_move: str = Field(description="Risposta o contromisura tattico-strategica.")


class BusinessFrameworkPayload(BaseModel):
    punchy_title: str = Field(description="Titolo assertivo e ad alta intensità.")
    intro: str = Field(description="Breve introduzione al concetto chiave.")
    core_principle: str = Field(description="Spiegazione logica del principio di leva o profitto.")
    framework_steps: List[str] = Field(
        description="Passaggi sequenziali del metodo operativo o domande da porsi."
    )
    strategy_table: List[FrameworkTableEntry] = Field(
        description="Tabella scenari e rispettive mosse strategiche."
    )
    case_lesson: str = Field(
        description="Aneddoto, caso studio o metrica chiave citata."
    )
    bottom_line: str = Field(description="Conclusione brutale orientata all'azione.")


class FrameworkExtractionOutput(BaseModel):
    digest: ExecutiveDigest
    notion_data: BusinessFrameworkPayload


# ─── CANALE CUMULATIVO: DAILY INTELLIGENCE BRIEFING ─────────────────
class DomainBriefingEntry(BaseModel):
    domain_name: str = Field(description="Nome della newsletter o dominio (es. 'The Crypto Gateway', 'Mozi Minute').")
    core_thesis: str = Field(description="Tesi o dinamica principale estratta oggi (1-2 frasi dense).")
    key_takeaways: List[str] = Field(description="2-3 bullet point chirurgici dei fatti e delle decisioni più importanti.")
    notion_url: Optional[str] = Field(default=None, description="URL diretto alla pagina Notion se disponibile.")


class DailyBriefingOutput(BaseModel):
    executive_title: str = Field(description="Titolo esecutivo del briefing giornaliero in italiano (max 10 parole).")
    macro_narrative: str = Field(description="Sintesi integrata ad altissima densità che collega i diversi temi della giornata in una visione sistemica (2-3 paragrafi compatti).")
    domain_breakdowns: List[DomainBriefingEntry] = Field(description="Riepilogo strutturato per ciascun dominio processato oggi.")
    actionable_priority: str = Field(description="La singola mossa o priorità strategico-operativa da tenere a mente per domani.")


# ─── SCHEMA REGISTRY PER DISPATCHING DINAMICO ────────────────────────
SCHEMA_REGISTRY: Dict[str, Type[BaseModel]] = {
    "quantitative_metrics": QuantitativeExtractionOutput,
    "journalistic_editorial": EditorialExtractionOutput,
    "business_framework": FrameworkExtractionOutput,
    "daily_briefing": DailyBriefingOutput,
}


def get_schema_for_type(schema_type: str) -> Type[BaseModel]:
    schema = SCHEMA_REGISTRY.get(schema_type)
    if not schema:
        raise ValueError(f"Schema type '{schema_type}' not found in SCHEMA_REGISTRY.")
    return schema
