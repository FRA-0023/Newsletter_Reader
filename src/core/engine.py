import time
import logging
from typing import Optional
from pathlib import Path

from config.settings import DomainConfig, GlobalRuntimeConfig, EnvSettings
from src.core.models import RawEmail
from src.adapters.sqlite_store import SQLiteStore
from src.adapters.imap_client import ImapClient
from src.adapters.gemini_client import GeminiClient, QuotaExhaustedError
from src.adapters.notion_client import NotionClientAdapter
from src.adapters.email_notifier import EmailNotifier

logger = logging.getLogger(__name__)


class NewsletterEngine:
    def __init__(
        self,
        global_config: GlobalRuntimeConfig,
        env_settings: EnvSettings,
        store: SQLiteStore,
    ):
        self.global_config = global_config
        self.env = env_settings
        self.store = store

        self.imap_client = ImapClient(
            username=self.env.GMAIL_USER,
            password=self.env.GMAIL_APP_PASSWORD,
            host=self.global_config.imap_server,
            port=self.global_config.imap_port,
        )

        self.gemini_client = GeminiClient(api_key=self.env.GEMINI_API_KEY) if self.env.GEMINI_API_KEY else None
        self.notion_client = NotionClientAdapter(token=self.env.NOTION_TOKEN) if self.env.NOTION_TOKEN else None
        self.email_notifier = EmailNotifier(
            username=self.env.GMAIL_USER,
            password=self.env.GMAIL_APP_PASSWORD,
            smtp_server=self.global_config.smtp_server,
            smtp_port=self.global_config.smtp_port,
        )

    def process_domain(self, domain: DomainConfig, dry_run: bool = False) -> int:
        logger.info(f"=== Starting processing for domain: [{domain.id}] '{domain.display_name}' ===")

        if not domain.enabled:
            logger.info(f"Domain '{domain.id}' is disabled in configuration. Skipping.")
            return 0

        # Resolve Notion Database ID from environment
        db_id = getattr(self.env, domain.notion.database_env_key, None)
        if not db_id and not dry_run:
            logger.error(
                f"Missing Notion database ID in environment variable: {domain.notion.database_env_key}"
            )
            return 0

        processed_count = 0

        with self.imap_client as imap:
            emails = imap.fetch_unread(
                sender_filter=domain.filter.sender,
                subject_filter=domain.filter.subject_contains,
                stop_string=domain.filter.stop_string,
            )

            if not emails:
                logger.info(f"No unread emails found for domain '{domain.id}'.")
                return 0

            logger.info(f"Discovered {len(emails)} unread email(s) for domain '{domain.id}'.")

            for i, email_item in enumerate(emails):
                mid = email_item.message_id
                if self.store.is_processed(mid):
                    logger.info(f"Skipping already processed email [MID: {mid}] Subject: '{email_item.subject}'")
                    continue

                logger.info(f"Processing ({i + 1}/{len(emails)}): '{email_item.subject}'")

                if not self.gemini_client:
                    logger.error("GEMINI_API_KEY is not configured.")
                    break

                try:
                    extraction_result = self.gemini_client.extract_structured_content(
                        template_path=domain.ai.prompt_template,
                        subject=email_item.subject,
                        body=email_item.body,
                        schema_type=domain.ai.schema_type,
                        model_name=domain.ai.model,
                        max_retries=self.global_config.max_retries,
                    )
                except QuotaExhaustedError as e:
                    logger.critical(f"Aborting domain processing due to Gemini quota exhaustion: {e}")
                    raise
                except Exception as e:
                    logger.error(f"Gemini synthesis failed for '{email_item.subject}': {e}", exc_info=True)
                    continue

                digest = extraction_result.digest
                notion_data = extraction_result.notion_data

                if dry_run:
                    logger.info("[DRY-RUN] Extraction succeeded:")
                    logger.info(f"  Headline: {digest.headline}")
                    logger.info(f"  Bullet 1: {digest.bullet_1}")
                    logger.info(f"  Bullet 2: {digest.bullet_2}")
                    logger.info(f"  Bullet 3: {digest.bullet_3}")
                    logger.info(f"  Notion Data: {notion_data}")
                    processed_count += 1
                    continue

                # 1. Save to Notion
                notion_page_id = None
                try:
                    if self.notion_client and db_id:
                        notion_page_id = self.notion_client.save_page(
                            database_id=db_id,
                            subject=email_item.subject,
                            date_str=email_item.date_str,
                            layout_type=domain.notion.layout_type,
                            notion_data=notion_data,
                        )
                except Exception as e:
                    logger.error(f"Notion save failed for '{email_item.subject}': {e}", exc_info=True)
                    continue

                # 2. Push Email Digest (3-Bullet Executive Memo)
                digest_sent = False
                if domain.digest.enabled:
                    recipient = domain.digest.recipient or self.env.DIGEST_RECIPIENT or self.env.GMAIL_USER
                    digest_sent = self.email_notifier.send_executive_digest(
                        recipient=recipient,
                        display_name=domain.display_name,
                        subject_prefix=domain.digest.subject_prefix,
                        digest=digest,
                        date_str=email_item.date_str,
                        notion_page_id=notion_page_id,
                    )

                # 3. Commit persistent state & flag on mail server
                self.store.record_processed(
                    message_id=mid,
                    domain_id=domain.id,
                    subject=email_item.subject,
                    notion_page_id=notion_page_id,
                    digest_sent=digest_sent,
                )

                try:
                    imap.mark_as_read(email_item.eid)
                except Exception as e:
                    logger.warning(f"Failed to flag email {email_item.eid} as read on IMAP: {e}")

                processed_count += 1
                logger.info(f"Successfully finished processing for '{email_item.subject}'.")

                if i < len(emails) - 1 and self.global_config.inter_email_delay_seconds > 0:
                    time.sleep(self.global_config.inter_email_delay_seconds)

        return processed_count
