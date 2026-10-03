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

        notion_url = f"https://notion.so/{notion_page_id.replace('-', '')}" if notion_page_id else ""
        notion_btn = f"""<div style="margin-top: 20px;">
            <a href="{notion_url}" style="display: inline-block; background-color: #0f172a; color: #ffffff; text-decoration: none; font-size: 13px; font-weight: 600; padding: 9px 18px; border-radius: 6px;">Apri scheda completa su Notion &rarr;</a>
        </div>""" if notion_url else ""

        body_html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; color: #0f172a; margin: 0; padding: 24px 12px; line-height: 1.5;">
    <div style="max-width: 580px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 28px 24px;">
        <div style="border-bottom: 1px solid #f1f5f9; padding-bottom: 14px; margin-bottom: 20px;">
            <span style="font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;">{display_name}</span>
            <h1 style="font-size: 20px; font-weight: 700; color: #0f172a; margin: 6px 0 2px 0; line-height: 1.3;">{digest.headline}</h1>
            <span style="font-size: 12px; color: #94a3b8;">{date_str} • Lettura rapida: 30 sec</span>
        </div>

        <div style="margin-bottom: 22px;">
            <div style="margin-bottom: 12px; padding: 12px 14px; background: #f8fafc; border-left: 3px solid #3b82f6; border-radius: 0 6px 6px 0;">
                <strong style="color: #1e3a8a; font-size: 12px; text-transform: uppercase; display: block; margin-bottom: 2px;">Dati & Fatti Chiave</strong>
                <span style="color: #1e293b; font-size: 14px; line-height: 1.5;">{digest.bullet_1}</span>
            </div>
            <div style="margin-bottom: 12px; padding: 12px 14px; background: #f8fafc; border-left: 3px solid #8b5cf6; border-radius: 0 6px 6px 0;">
                <strong style="color: #5b21b6; font-size: 12px; text-transform: uppercase; display: block; margin-bottom: 2px;">Dinamica & Contesto</strong>
                <span style="color: #1e293b; font-size: 14px; line-height: 1.5;">{digest.bullet_2}</span>
            </div>
            <div style="margin-bottom: 12px; padding: 12px 14px; background: #f8fafc; border-left: 3px solid #10b981; border-radius: 0 6px 6px 0;">
                <strong style="color: #065f46; font-size: 12px; text-transform: uppercase; display: block; margin-bottom: 2px;">Azione & Takeaway</strong>
                <span style="color: #1e293b; font-size: 14px; line-height: 1.5;">{digest.bullet_3}</span>
            </div>
        </div>

        {notion_btn}

        <div style="margin-top: 28px; padding-top: 14px; border-top: 1px solid #f1f5f9; font-size: 11.5px; color: #94a3b8; text-align: center;">
            Newsletter_Reader Engine &bull; Approfondimenti completi e schede strutturate salvati su Notion.
        </div>
    </div>
</body>
</html>"""

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{display_name} <{self.username}>"
        msg["To"] = to_email

        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        msg.attach(MIMEText(body_html, "html", "utf-8"))

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

    def send_daily_briefing(
        self,
        recipient: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
    ) -> bool:
        if not self.username or not self.password:
            logger.warning("SMTP credentials not configured. Skipping daily briefing email.")
            return False

        to_email = recipient or self.username

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Executive Intelligence Briefing <{self.username}>"
        msg["To"] = to_email

        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        if body_html:
            msg.attach(MIMEText(body_html, "html", "utf-8"))

        try:
            logger.info(f"Sending daily briefing email to {to_email} via SMTP SSL {self.smtp_server}:{self.smtp_port}...")
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=20) as server:
                server.login(self.username, self.password)
                server.send_message(msg)
            logger.info("Daily briefing email sent successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to send daily briefing email: {e}", exc_info=True)
            return False
