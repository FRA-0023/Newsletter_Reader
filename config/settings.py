from pathlib import Path
from typing import Optional, List, Dict, Any
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ScheduleConfig(BaseModel):
    cron: str
    timezone: str = "Europe/Rome"


class FilterConfig(BaseModel):
    sender: str
    subject_contains: str = ""
    stop_string: Optional[str] = None


class AIConfig(BaseModel):
    model: str = "gemini-2.5-flash"
    prompt_template: str
    schema_type: str


class NotionConfig(BaseModel):
    database_env_key: Optional[str] = None
    database_id: Optional[str] = None
    layout_type: str


class DigestConfig(BaseModel):
    # ARCHITETTURA / CARICO COGNITIVO: Disabilitato di default. L'unica notifica push
    # via email desiderata è il Daily Briefing serale cumulativo delle 20:00.
    # Le newsletter individuali alimentano unicamente Notion e il database SQLite.
    enabled: bool = False
    subject_prefix: str = "[DIGEST]"
    recipient: Optional[str] = None


class DomainConfig(BaseModel):
    id: str
    display_name: str
    enabled: bool = True
    schedule: ScheduleConfig
    filter: FilterConfig
    ai: AIConfig
    notion: NotionConfig
    digest: DigestConfig = Field(default_factory=DigestConfig)


class GlobalRuntimeConfig(BaseModel):
    imap_server: str = "imap.gmail.com"
    imap_port: int = 993
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 465
    max_retries: int = 3
    inter_email_delay_seconds: float = 5.0
    db_path: str = "data/state.db"
    language: str = "en"


class DailyBriefingScheduleConfig(BaseModel):
    enabled: bool = True
    schedule: ScheduleConfig = Field(
        default_factory=lambda: ScheduleConfig(cron="0 20 * * *", timezone="Europe/Rome")
    )
    subject_prefix: str = "[DAILY BRIEFING]"
    prompt_template: str = "templates/daily_briefing.md"


class YamlConfig(BaseModel):
    version: str = "1.0"
    global_: GlobalRuntimeConfig = Field(alias="global", default_factory=GlobalRuntimeConfig)
    daily_briefing: DailyBriefingScheduleConfig = Field(default_factory=DailyBriefingScheduleConfig)
    domains: List[DomainConfig] = Field(default_factory=list)


class EnvSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    GMAIL_USER: str = ""
    GMAIL_APP_PASSWORD: str = ""
    GEMINI_API_KEY: str = ""
    NOTION_TOKEN: str = ""

    # Specific database IDs mapped to environment variables
    NOTION_DB_WORLD_POPULATION: str = ""
    NOTION_DB_CRYPTO: str = ""
    NOTION_DB_MOZI: str = ""
    NOTION_DB_TRISTAN_BURNS: str = ""
    NOTION_DB_DAVID_COHEN: str = ""

    # Explicit environment localization override (e.g. 'en', 'it', 'es').
    # If omitted from .env, cascades to global.language defined in config/domains.yaml
    LANGUAGE: Optional[str] = None

    # Optional dedicated Notion Database for Evening Daily Intelligence Briefings
    NOTION_DB_DAILY_BRIEFING: Optional[str] = None

    DIGEST_RECIPIENT: str = ""
    DATA_DIR: str = str(PROJECT_ROOT / "data")
    LOG_LEVEL: str = "INFO"


def load_yaml_config(config_path: Optional[Path] = None) -> YamlConfig:
    if config_path is None:
        config_path = PROJECT_ROOT / "config" / "domains.yaml"
        if not config_path.exists():
            example_path = PROJECT_ROOT / "config" / "domains.example.yaml"
            if example_path.exists():
                config_path = example_path

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    return YamlConfig.model_validate(raw)


def resolve_language(env_lang: Optional[str], yaml_lang: Optional[str]) -> str:
    """
    Determines output localization language following strict cascade hierarchy:
    1. Explicit environment variable override (LANGUAGE in .env)
    2. Global configuration in domains.yaml (global.language)
    3. Canonical fallback: 'en' for open-source distribution consistency.
    """
    if env_lang and env_lang.strip():
        return env_lang.strip().lower()
    if yaml_lang and yaml_lang.strip():
        return yaml_lang.strip().lower()
    return "en"

