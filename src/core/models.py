from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class RawEmail:
    eid: str
    message_id: str
    sender: str
    subject: str
    date_str: str
    body: str


@dataclass
class ProcessedRecord:
    message_id: str
    domain_id: str
    subject: str
    notion_page_id: Optional[str]
    digest_sent: bool
    processed_at: datetime
