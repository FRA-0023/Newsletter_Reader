import logging
from typing import Optional, List, Dict, Any
from datetime import date
from pathlib import Path

from config.settings import GlobalRuntimeConfig, EnvSettings, YamlConfig
from src.adapters.sqlite_store import SQLiteStore
from src.adapters.gemini_client import GeminiClient
from src.adapters.email_notifier import EmailNotifier
from src.core.schemas import DailyBriefingOutput

logger = logging.getLogger(__name__)


class DailyBriefingService:
    def __init__(
        self,
        global_config: GlobalRuntimeConfig,
        env_settings: EnvSettings,
        store: SQLiteStore,
        yaml_config: YamlConfig,
    ):
        self.global_config = global_config
        self.env = env_settings
        self.store = store
        self.yaml_config = yaml_config
        self.gemini_client = GeminiClient(api_key=self.env.GEMINI_API_KEY) if self.env.GEMINI_API_KEY else None
        self.email_notifier = EmailNotifier(
            username=self.env.GMAIL_USER,
            password=self.env.GMAIL_APP_PASSWORD,
            smtp_server=self.global_config.smtp_server,
            smtp_port=self.global_config.smtp_port,
        )

    def generate_and_send(
        self,
        target_date: Optional[str] = None,
        dry_run: bool = False,
        recipient_override: Optional[str] = None,
    ) -> bool:
        if target_date is None:
            target_date = date.today().isoformat()

        logger.info(f"=== Initiating Daily Briefing Generation for date: {target_date} ===")

        records = self.store.get_records_by_date(target_date)
        if not records:
            logger.info(f"No processed newsletter records found in SQLite database for {target_date}. Skipping briefing.")
            return False

        logger.info(f"Found {len(records)} record(s) processed on {target_date} to synthesize.")

        # Map domain_id to display_name
        domain_names = {d.id: d.display_name for d in self.yaml_config.domains}

        # Build input context for Gemini
        intake_blocks: List[str] = []
        for idx, rec in enumerate(records, 1):
            d_name = domain_names.get(rec["domain_id"], rec["domain_id"].replace("_", " ").title())
            subject = rec.get("subject", "")
            headline = rec.get("headline", subject)
            b1 = rec.get("bullet_1", "")
            b2 = rec.get("bullet_2", "")
            b3 = rec.get("bullet_3", "")
            notion_id = rec.get("notion_page_id")
            notion_url = f"https://notion.so/{notion_id.replace('-', '')}" if notion_id else "N/A"

            block = f"""--- RECORD {idx}: [{d_name}] ---
Subject: {subject}
Headline: {headline}
• Fact/Data: {b1}
• Dynamic: {b2}
• Action/Takeaway: {b3}
Notion Page: {notion_url}
"""
            intake_blocks.append(block)

        aggregated_input = "\n".join(intake_blocks)

        if not self.gemini_client:
            logger.error("GEMINI_API_KEY is missing. Cannot synthesize daily briefing.")
            return False

        try:
            briefing_data: DailyBriefingOutput = self.gemini_client.extract_structured_content(
                template_path="templates/daily_briefing.md",
                subject=f"Daily Intelligence Synthesis - {target_date}",
                body=aggregated_input,
                schema_type="daily_briefing",
                model_name="gemini-2.5-flash",
            )
        except Exception as e:
            logger.error(f"Failed to generate Daily Briefing via Gemini: {e}", exc_info=True)
            return False

        # Format Text and HTML email
        subject_line = f"[DAILY INTEL BRIEFING] {target_date} — {briefing_data.executive_title}"
        body_text, body_html = self._render_email(target_date, briefing_data)

        if dry_run:
            logger.info("[DRY-RUN] Daily Briefing synthesized successfully:")
            logger.info(f"Subject: {subject_line}")
            logger.info(f"Text Content:\n{body_text}")
            return True

        raw_recipient = recipient_override or self.env.DIGEST_RECIPIENT or self.env.GMAIL_USER
        recipient = self.env.GMAIL_USER if raw_recipient in ("your_email@gmail.com", "your_email@example.com", "") else raw_recipient
        success = self.email_notifier.send_daily_briefing(
            recipient=recipient,
            subject=subject_line,
            body_text=body_text,
            body_html=body_html,
        )

        if success:
            logger.info(f"Daily Briefing for {target_date} dispatched to {recipient}.")
        return success

    def _render_email(self, date_str: str, data: DailyBriefingOutput) -> tuple[str, str]:
        # Plain text rendering
        lines: List[str] = [
            f"DAILY INTELLIGENCE BRIEFING — {date_str}",
            f"{'=' * 50}",
            f"OVERVIEW: {data.executive_title}",
            "",
            "MACRO NARRATIVE & CAUSAL CONNECTIONS:",
            data.macro_narrative,
            "",
            f"{'-' * 50}",
            "DOMAIN BREAKDOWNS:",
            "",
        ]

        for d in data.domain_breakdowns:
            lines.append(f"■ {d.domain_name.upper()}")
            lines.append(f"  Thesis: {d.core_thesis}")
            for b in d.key_takeaways:
                lines.append(f"  • {b}")
            if d.notion_url:
                lines.append(f"  Notion: {d.notion_url}")
            lines.append("")

        lines.extend([
            f"{'-' * 50}",
            f"STRATEGIC PRIORITY FOR TOMORROW:",
            f"🎯 {data.actionable_priority}",
            "",
            f"{'=' * 50}",
            "Archived & Synthesized by Newsletter_Reader Headless Engine.",
        ])

        body_text = "\n".join(lines)

        # Minimalist responsive executive HTML
        html_domains = []
        for d in data.domain_breakdowns:
            bullets_html = "".join([
                f"<li style='margin-bottom: 8px; font-size: 13.5px; color: #334155; line-height: 1.55;'>• {b}</li>"
                for b in d.key_takeaways
            ])
            notion_link = (
                f"<div style='margin-top: 14px;'>"
                f"<a href='{d.notion_url}' style='display: inline-block; background-color: #0f172a; color: #ffffff; text-decoration: none; font-size: 12px; font-weight: 600; padding: 7px 15px; border-radius: 6px;'>Approfondisci su Notion &rarr;</a>"
                f"</div>"
                if d.notion_url else ""
            )
            html_domains.append(f"""
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 18px 20px; margin-bottom: 16px;">
                <h3 style="margin: 0 0 6px 0; color: #0f172a; font-size: 15.5px; font-weight: 700;">{d.domain_name}</h3>
                <p style="margin: 0 0 12px 0; color: #475569; font-size: 13.5px; line-height: 1.5; font-style: italic;">{d.core_thesis}</p>
                <ul style="margin: 0; padding-left: 0; list-style: none;">
                    {bullets_html}
                </ul>
                {notion_link}
            </div>
            """)

        body_html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; color: #0f172a; margin: 0; padding: 24px 12px; line-height: 1.5;">
    <div style="max-width: 580px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 28px 24px;">
        <div style="border-bottom: 1px solid #f1f5f9; padding-bottom: 14px; margin-bottom: 20px;">
            <span style="font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;">☕ Daily Intelligence Briefing</span>
            <h1 style="font-size: 20px; font-weight: 700; color: #0f172a; margin: 6px 0 2px 0; line-height: 1.3;">{data.executive_title}</h1>
            <span style="font-size: 12px; color: #94a3b8;">Data: {date_str} • Lettura rapida: 60 sec</span>
        </div>

        <div style="margin-bottom: 22px; background: #f8fafc; border-left: 3px solid #3b82f6; border-radius: 0 8px 8px 0; padding: 14px 16px;">
            <span style="font-size: 11px; font-weight: 700; color: #1e40af; text-transform: uppercase; display: block; margin-bottom: 4px; letter-spacing: 0.03em;">Panoramica in Breve</span>
            <p style="font-size: 13.5px; color: #334155; line-height: 1.6; margin: 0;">
                {data.macro_narrative}
            </p>
        </div>

        <div style="margin-bottom: 22px;">
            <h2 style="font-size: 11.5px; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; margin: 0 0 12px 0; font-weight: 700;">I Punti Salienti di Oggi</h2>
            {"".join(html_domains)}
        </div>

        <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 10px; padding: 16px 18px; margin-bottom: 22px;">
            <span style="font-size: 11px; font-weight: 700; color: #166534; text-transform: uppercase; letter-spacing: 0.05em;">🎯 Spunto per Domani</span>
            <p style="margin: 6px 0 0 0; color: #14532d; font-weight: 600; font-size: 13.5px; line-height: 1.5;">{data.actionable_priority}</p>
        </div>

        <div style="font-size: 11.5px; color: #94a3b8; border-top: 1px solid #f1f5f9; padding-top: 16px; text-align: center;">
            Newsletter_Reader &bull; Gli approfondimenti e le schede complete sono archiviati sul tuo Notion.
        </div>
    </div>
</body>
</html>"""
        return body_text, body_html
