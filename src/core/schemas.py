from typing import List, Optional, Dict, Type
from pydantic import BaseModel, Field


# ─── CANALE PUSH: EXECUTIVE EMAIL DIGEST (MASSIMO 3 BULLET POINT) ───
# ARCHITETTURA: I campi di ExecutiveDigest sono convertiti in JSON Schema per Gemini Structured Outputs.
# Le descrizioni guidano direttamente la fedeltà estrattiva: devono consentire sia il rigore statistico/demografico
# (definizione, fonti, prevalenza) sia la logica di business (problema, principio, azione) senza distorsioni.
class ExecutiveDigest(BaseModel):
    headline: str = Field(
        description="Sintesi telegrafica e incisiva dell'argomento principale (max 10-12 parole)."
    )
    bullet_1: str = Field(
        description="Punto 1: Cos'è il soggetto trattato, qual è la sua funzione primaria (biologica, sociale o di mercato), e dove si trova o come viene ottenuto/originato (o problema cardine per business)."
    )
    bullet_2: str = Field(
        description="Punto 2: Dati quantitativi chiave, percentuali, cause sottostanti o dinamiche sistemiche."
    )
    bullet_3: str = Field(
        description="Punto 3: Conseguenze, impatto clinico/economico/sociale o azione/decisione operativa."
    )


# ─── CANALE STORAGE: STRUTTURA WORLD POPULATION ─────────────────────
# TRADE-OFF: Manteniamo data_points come lista di stringhe per flessibilità di rendering in Notion,
# ma imponiamo tramite schema la copertura esaustiva: definizione, funzione/fonti, metriche, cause ed effetti.
class QuantitativeMetricsPayload(BaseModel):
    macro_topic: str = Field(
        description="Classificazione sintetica in 1-3 parole (es. Salute & Epidemiologia, Demografia Globale)."
    )
    data_points: List[str] = Field(
        description="Elenco ordinato di 4-8 evidenze analitiche con contesto completo: definizione, ruolo/fonti del soggetto, metriche quantitative esatte, fattori causali e impatto/raccomandazioni."
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
# ARCHITETTURA: Schema del briefing cumulativo serale inviato via email e archiviato su Notion.
# I vincoli stringenti nelle descrizioni dei campi istruiscono il modello a livello di JSON schema,
# prevenendo allucinazioni di meta-narrative olistiche o chimere di domini eterogenei.
class DomainBriefingEntry(BaseModel):
    domain_name: str = Field(description="Nome della newsletter e del tema specifico (es. 'Tristan Burns — Jobs to Be Done in Data Teams').")
    core_thesis: Optional[str] = Field(default=None, description="Opzionale sintesi diagnostica (omessa o null per evitare duplicazioni con i takeaways).")
    key_takeaways: List[str] = Field(description="Esattamente 3 bullet point distinti e non sovrapposti con tag in grassetto (es. Problema/Contesto, Meccanismo/Funzione, Implicazione/Azione).")
    notion_url: Optional[str] = Field(default=None, description="URL diretto alla pagina Notion della specifica email.")


class DailyBriefingOutput(BaseModel):
    executive_title: str = Field(description="Titolo esecutivo in italiano (max 8-10 parole) che riflette i macro-temi del giorno senza forzature unificanti (es. 'Radar Odierno: Focus Demografia, Strategia d'Impresa & Mercati').")
    macro_narrative: str = Field(description="Panoramica esecutiva asettica (2-3 frasi chiare) che sintetizza i fronti principali della giornata per macro-aree, SENZA forzare collegamenti artificiali, finti contrasti o narrazioni olistiche tra temi non correlati.")
    domain_breakdowns: List[DomainBriefingEntry] = Field(description="Riepilogo strutturato per ciascun dominio processato oggi (mappatura rigorosa 1:1).")
    actionable_priority: str = Field(description="Un singolo spunto operativo o test diagnostico focalizzato, estratto da uno specifico dominio applicabile (es. strategia/business). SEVERAMENTE VIETATO mescolare o fondere più domini diversi in una singola frase.")


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
