import imaplib
import email
import email.utils
from email.header import decode_header
import logging
from typing import List, Optional
import html2text

from src.core.models import RawEmail

logger = logging.getLogger(__name__)


class ImapClient:
    def __init__(
        self,
        username: str,
        password: str,
        host: str = "imap.gmail.com",
        port: int = 993,
        timeout: float = 30.0,
    ):
        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.timeout = timeout
        self.mail: Optional[imaplib.IMAP4_SSL] = None

    def __enter__(self) -> "ImapClient":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()

    def connect(self) -> None:
        logger.info(f"Connecting to IMAP {self.host}:{self.port} as {self.username}...")
        self.mail = imaplib.IMAP4_SSL(self.host, self.port)
        self.mail.login(self.username, self.password)
        self.mail.select("inbox")
        logger.info("IMAP connected successfully and inbox selected.")

    def disconnect(self) -> None:
        if self.mail:
            try:
                self.mail.close()
            except Exception:
                pass
            try:
                self.mail.logout()
            except Exception:
                pass
            self.mail = None
            logger.debug("IMAP session closed.")

    def fetch_unread(
        self,
        sender_filter: str,
        subject_filter: str = "",
        stop_string: Optional[str] = None,
    ) -> List[RawEmail]:
        if not self.mail:
            raise RuntimeError("IMAP client is not connected.")

        search_criteria = f'(UNSEEN FROM "{sender_filter}")'
        logger.info(f"Searching IMAP inbox with criteria: {search_criteria}")
        status, data = self.mail.search(None, search_criteria)

        if status != "OK" or not data or not data[0]:
            logger.info("No unread emails found matching criteria.")
            return []

        email_ids = data[0].split()
        logger.info(f"Found {len(email_ids)} unread email(s) for sender: {sender_filter}")
        results: List[RawEmail] = []

        for eid_bytes in email_ids:
            eid = eid_bytes.decode("utf-8")
            status, msg_data = self.mail.fetch(eid, "(RFC822)")
            if status != "OK" or not msg_data:
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject = self._decode_header(msg.get("Subject", "Senza Titolo"))
            sender = self._decode_header(msg.get("From", ""))
            date_str = msg.get("Date", "")
            message_id = msg.get("Message-ID", f"fallback-{eid}-{date_str}").strip()

            if subject_filter and subject_filter.lower() not in subject.lower():
                logger.info(f"Skipping email '{subject}' (does not match subject filter '{subject_filter}')")
                continue

            body = self._extract_body(msg)

            # Truncate at stop_string if present
            if stop_string and stop_string in body:
                logger.info(f"Truncating email body at stop string: '{stop_string}'")
                body = body.split(stop_string)[0].strip()

            results.append(
                RawEmail(
                    eid=eid,
                    message_id=message_id,
                    sender=sender,
                    subject=subject,
                    date_str=date_str,
                    body=body,
                )
            )

        return results

    def mark_as_read(self, eid: str) -> None:
        if not self.mail:
            raise RuntimeError("IMAP client is not connected.")
        self.mail.store(eid, "+FLAGS", "\\Seen")
        logger.info(f"Flagged email UID {eid} as \\Seen on Gmail.")

    def _decode_header(self, raw_header: Optional[str]) -> str:
        if not raw_header:
            return ""
        decoded_parts = decode_header(raw_header)
        result = []
        for content, enc in decoded_parts:
            if isinstance(content, bytes):
                result.append(content.decode(enc or "utf-8", errors="ignore"))
            else:
                result.append(str(content))
        return "".join(result).strip()

    def _extract_body(self, msg: email.message.Message) -> str:
        h2t = html2text.HTML2Text()
        h2t.ignore_links = True
        h2t.ignore_images = True
        h2t.body_width = 0

        plain_text = ""
        html_text = ""

        if msg.is_multipart():
            for part in msg.walk():
                ct = part.get_content_type()
                if ct == "text/plain" and not plain_text:
                    payload = part.get_payload(decode=True)
                    if payload:
                        plain_text = payload.decode("utf-8", errors="ignore")
                elif ct == "text/html" and not html_text:
                    payload = part.get_payload(decode=True)
                    if payload:
                        html_text = payload.decode("utf-8", errors="ignore")
        else:
            ct = msg.get_content_type()
            payload = msg.get_payload(decode=True)
            if payload:
                text = payload.decode("utf-8", errors="ignore")
                if ct == "text/html":
                    html_text = text
                else:
                    plain_text = text

        if plain_text:
            return plain_text.strip()
        if html_text:
            return h2t.handle(html_text).strip()
        return ""
