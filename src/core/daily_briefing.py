import re
import logging
from typing import Optional, List, Dict, Any
from datetime import date
from pathlib import Path

from config.settings import GlobalRuntimeConfig, EnvSettings, YamlConfig, resolve_language
from src.adapters.sqlite_store import SQLiteStore
from src.adapters.gemini_client import GeminiClient
from src.adapters.email_notifier import EmailNotifier
from src.core.schemas import DailyBriefingOutput

logger = logging.getLogger(__name__)

# Curated, high-contrast, accessible color accents for domain visual distinction.
# Each entry defines a left-border accent and an executive pill badge.
DOMAIN_ACCENTS = [
    {"border": "#2563eb", "badge_bg": "#eff6ff", "badge_text": "#1d4ed8", "badge_border": "#bfdbfe"},  # Cobalt Blue
    {"border": "#7c3aed", "badge_bg": "#f5f3ff", "badge_text": "#6d28d9", "badge_border": "#ddd6fe"},  # Royal Violet
    {"border": "#059669", "badge_bg": "#ecfdf5", "badge_text": "#047857", "badge_border": "#a7f3d0"},  # Emerald Green
    {"border": "#d97706", "badge_bg": "#fffbeb", "badge_text": "#b45309", "badge_border": "#fde68a"},  # Amber Warm
    {"border": "#e11d48", "badge_bg": "#fff1f2", "badge_text": "#be123c", "badge_border": "#fecdd3"},  # Crimson Rose
    {"border": "#0891b2", "badge_bg": "#ecfeff", "badge_text": "#0e7490", "badge_border": "#a5f3fc"},  # Ocean Cyan
]


def _clean_html_markdown(text: str) -> str:
    """
    Converts LLM markdown tokens into styled HTML tags and strips accidental leading bullet symbols.
    
    Trade-off: LLMs regularly emit markdown (e.g. **bold**, *italics*, `code`) even in structured JSON strings.
    Parsing via targeted regex guarantees flawless cross-client email rendering without heavy AST dependencies.
    """
    if not text:
        return ""
    # Strip any accidental leading bullet points like "• ", "- ", or "* "
    cleaned = re.sub(r'^[•\-\*]\s*', '', text.strip())
    # Bold: **phrase** -> <strong style="color: #0f172a; font-weight: 700;">phrase</strong>
    cleaned = re.sub(r'\*\*(.*?)\*\*', r'<strong style="color: #0f172a; font-weight: 700;">\1</strong>', cleaned)
    # Italic: *phrase* -> <em>phrase</em>
    cleaned = re.sub(r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)', r'<em>\1</em>', cleaned)
    # Inline code: `token` -> <code>token</code>
    cleaned = re.sub(r'`(.*?)`', r'<code style="background: #f1f5f9; padding: 2px 4px; border-radius: 4px; font-size: 12px;">\1</code>', cleaned)
    return cleaned


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

        target_lang = resolve_language(self.env.LANGUAGE, getattr(self.global_config, "language", "en"))

        try:
            briefing_data: DailyBriefingOutput = self.gemini_client.extract_structured_content(
                template_path="templates/daily_briefing.md",
                subject=f"Daily Intelligence Synthesis - {target_date}",
                body=aggregated_input,
                schema_type="daily_briefing",
                model_name="gemini-2.5-flash",
                language=target_lang,
            )
        except Exception as e:
            logger.error(f"Failed to generate Daily Briefing via Gemini: {e}", exc_info=True)
            return False

        # Dual-layer persistence: First attempt Notion sync if a target database is configured.
        # Notion provides high-visibility executive mobile access and inter-page relational navigation.
        notion_page_id = None
        if not dry_run and self.env.NOTION_DB_DAILY_BRIEFING and self.notion_client:
            try:
                notion_page_id = self.notion_client.save_daily_briefing_page(
                    database_id=self.env.NOTION_DB_DAILY_BRIEFING,
                    date_str=target_date,
                    data=briefing_data,
                    language=target_lang,
                )
                logger.info(f"Daily Briefing archived in Notion database with Page ID: {notion_page_id}")
            except Exception as e:
                logger.error(f"Failed to persist Daily Briefing to Notion: {e}", exc_info=True)

        # Local SQLite state persistence guarantees offline auditability and idempotency.
        # This prevents total data loss if network partitions disrupt Notion or SMTP delivery.
        if not dry_run:
            self.store.record_daily_briefing(
                date_str=target_date,
                executive_title=briefing_data.executive_title,
                macro_narrative=briefing_data.macro_narrative,
                actionable_priority=briefing_data.actionable_priority,
                domain_count=len(briefing_data.domain_breakdowns),
                raw_json=briefing_data.model_dump_json(),
                notion_page_id=notion_page_id,
            )

        # Format Text and HTML email
        subject_line = f"[DAILY INTEL BRIEFING] {target_date} — {briefing_data.executive_title}"
        body_text, body_html = self._render_email(
            target_date, briefing_data, notion_page_id=notion_page_id, language=target_lang
        )

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

    def _render_email(
        self,
        date_str: str,
        data: DailyBriefingOutput,
        notion_page_id: Optional[str] = None,
        language: str = "en",
    ) -> tuple[str, str]:
        # Internationalized string catalog: renders email UI chrome in the operator's configured language.
        is_it = language.lower() == "it"

        lbl_header = "☕ Daily Intelligence Briefing"
        lbl_read_time = "Lettura rapida: 60 sec" if is_it else "Quick read: 60 sec"
        lbl_date = "Data:" if is_it else "Date:"
        lbl_overview = "Panoramica in Breve" if is_it else "Executive Overview"
        lbl_highlights = "I Punti Salienti di Oggi" if is_it else "Today's Core Highlights"
        lbl_priority = "🎯 Spunto per Domani" if is_it else "🎯 Actionable Priority for Tomorrow"
        lbl_notion_btn = "Approfondisci su Notion &rarr;" if is_it else "Explore on Notion &rarr;"
        lbl_footer = (
            "Newsletter_Reader &bull; Gli approfondimenti completi sono archiviati sul tuo Notion."
            if is_it
            else "Newsletter_Reader &bull; Full deep-dive notes and frameworks are archived in your Notion workspace."
        )

        notion_briefing_bar = ""
        if notion_page_id:
            clean_pid = notion_page_id.replace("-", "")
            btn_txt = "Apri Briefing su Notion" if is_it else "Open Briefing on Notion"
            notion_briefing_bar = (
                f"<div style='margin-bottom: 18px; text-align: right;'>"
                f"<a href='https://notion.so/{clean_pid}' style='font-size: 12px; font-weight: 600; color: #2563eb; text-decoration: none; background: #eff6ff; padding: 5px 12px; border-radius: 6px; border: 1px solid #bfdbfe;'>🔗 {btn_txt} &rarr;</a>"
                f"</div>"
            )

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

        # Minimalist responsive executive HTML with chromatic domain identification
        html_domains = []
        for idx, d in enumerate(data.domain_breakdowns):
            accent = DOMAIN_ACCENTS[idx % len(DOMAIN_ACCENTS)]
            border_color = accent['border']
            bullets_html = "".join([
                f"<li style='margin-bottom: 9px; font-size: 13.5px; color: #334155; line-height: 1.55; padding-left: 2px;'>"
                f"<span style='color: {border_color}; font-weight: bold; margin-right: 6px;'>•</span>"
                f"{_clean_html_markdown(b)}"
                f"</li>"
                for b in d.key_takeaways
            ])
            notion_link = (
                f"<div style='margin-top: 14px;'>"
                f"<a href='{d.notion_url}' style='display: inline-block; background-color: #0f172a; color: #ffffff; text-decoration: none; font-size: 12px; font-weight: 600; padding: 7px 15px; border-radius: 6px;'>{lbl_notion_btn}</a>"
                f"</div>"
                if d.notion_url else ""
            )
            html_domains.append(f"""
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-left: 4px solid {accent['border']}; border-radius: 10px; padding: 18px 20px; margin-bottom: 18px; box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);">
                <div style="margin-bottom: 8px;">
                    <span style="background: {accent['badge_bg']}; color: {accent['badge_text']}; border: 1px solid {accent['badge_border']}; font-size: 11px; font-weight: 700; text-transform: uppercase; padding: 2px 8px; border-radius: 4px; letter-spacing: 0.05em; display: inline-block;">{d.domain_name}</span>
                </div>
                <p style="margin: 0 0 12px 0; color: #475569; font-size: 13.5px; line-height: 1.5; font-style: italic;">{_clean_html_markdown(d.core_thesis)}</p>
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
            <span style="font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;">{lbl_header}</span>
            <h1 style="font-size: 20px; font-weight: 700; color: #0f172a; margin: 6px 0 2px 0; line-height: 1.3;">{_clean_html_markdown(data.executive_title)}</h1>
            <span style="font-size: 12px; color: #94a3b8;">{lbl_date} {date_str} • {lbl_read_time}</span>
        </div>

        {notion_briefing_bar}

        <div style="margin-bottom: 24px; padding-bottom: 18px; border-bottom: 1px solid #f1f5f9;">
            <span style="font-size: 11px; font-weight: 700; color: #2563eb; text-transform: uppercase; display: block; margin-bottom: 6px; letter-spacing: 0.05em;">{lbl_overview}</span>
            <p style="font-size: 14.5px; color: #1e293b; line-height: 1.65; margin: 0; font-weight: 400;">
                {_clean_html_markdown(data.macro_narrative)}
            </p>
        </div>

        <div style="margin-bottom: 22px;">
            <h2 style="font-size: 11.5px; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; margin: 0 0 12px 0; font-weight: 700;">{lbl_highlights}</h2>
            {"".join(html_domains)}
        </div>

        <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 10px; padding: 16px 18px; margin-bottom: 22px;">
            <span style="font-size: 11px; font-weight: 700; color: #166534; text-transform: uppercase; letter-spacing: 0.05em;">{lbl_priority}</span>
            <p style="margin: 6px 0 0 0; color: #14532d; font-weight: 600; font-size: 13.5px; line-height: 1.5;">{_clean_html_markdown(data.actionable_priority)}</p>
        </div>

        <div style="font-size: 11.5px; color: #94a3b8; border-top: 1px solid #f1f5f9; padding-top: 16px; text-align: center;">
            {lbl_footer}
        </div>
    </div>
</body>
</html>"""
        return body_text, body_html
