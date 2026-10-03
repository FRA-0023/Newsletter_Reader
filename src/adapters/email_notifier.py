import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from typing import Optional

from src.core.schemas import ExecutiveDigest

logger = logging.getLogger(__name__)


class EmailNotifier:
    def __init__(
        self,
        username: str,
        password: str,
        smtp_server: str = "smtp.gmail.com",
        smtp_port: int = 465,
    ):
        self.username = username
        self.password = password
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port

    def send_executive_digest(
        self,
        recipient: str,
        display_name: str,
        subject_prefix: str,
        digest: ExecutiveDigest,
        date_str: str,
        notion_page_id: Optional[str] = None,
    ) -> bool:
        if not self.username or not self.password:
            logger.warning("SMTP credentials not configured. Skipping digest email.")
            return False

        to_email = recipient or self.username
        subject = f"{subject_prefix} {digest.headline}".strip()

        notion_footer = ""
        if notion_page_id:
            # Notion page URL format
            clean_id = notion_page_id.replace("-", "")
            notion_footer = f"\n\nArchiviato su Notion: https://notion.so/{clean_id}"

        body_text = f"""{display_name} — {date_str}
Headline: {digest.headline}

• DATI: {digest.bullet_1}
• DINAMICA: {digest.bullet_2}
• TAKEAWAY: {digest.bullet_3}{notion_footer}
"""

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{display_name} <{self.username}>"
        msg["To"] = to_email

        msg.attach(MIMEText(body_text, "plain", "utf-8"))

        try:
            logger.info(f"Sending executive digest to {to_email} via SMTP SSL {self.smtp_server}:{self.smtp_port}...")
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=15) as server:
                server.login(self.username, self.password)
                server.send_message(msg)
            logger.info("Executive digest email sent successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to send executive digest email: {e}", exc_info=True)
            return False
