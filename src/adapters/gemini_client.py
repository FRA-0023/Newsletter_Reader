import json
import logging
import time
from pathlib import Path
from typing import Type, Optional
from pydantic import BaseModel
from google import genai
from google.genai import types

from src.core.schemas import get_schema_for_type

logger = logging.getLogger(__name__)


class GeminiClient:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("GEMINI_API_KEY must be provided.")
        self.api_key = api_key
        self.client = genai.Client(api_key=self.api_key)

    def extract_structured_content(
        self,
        template_path: str,
        subject: str,
        body: str,
        schema_type: str,
        model_name: str = "gemini-2.5-flash",
        max_retries: int = 3,
    ) -> BaseModel:
        p_path = Path(template_path)
        if not p_path.is_absolute():
            # Resolve relative to project root
            project_root = Path(__file__).resolve().parent.parent.parent
            p_path = project_root / template_path

        if not p_path.exists():
            raise FileNotFoundError(f"Prompt template file not found: {p_path}")

        template_content = p_path.read_text(encoding="utf-8")
        schema_class = get_schema_for_type(schema_type)

        full_prompt = f"""{template_content}

# INPUT EMAIL DATA
Subject: {subject}

{body}
"""

        attempts = 0
        backoff = 3.0
        rate_limit_delay = 30.0

        while attempts < max_retries:
            attempts += 1
            try:
                logger.info(
                    f"Invoking Gemini ({model_name}) with schema '{schema_type}' (Attempt {attempts}/{max_retries})..."
                )

                response = self.client.models.generate_content(
                    model=model_name,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=schema_class,
                    ),
                )

                raw_text = response.text.strip()
                logger.debug(f"Raw Gemini response length: {len(raw_text)} chars")

                # Parse and validate with Pydantic
                parsed_data = schema_class.model_validate_json(raw_text)
                return parsed_data

            except Exception as e:
                err_str = str(e)
                status_code = getattr(e, "code", None)

                # ── 1. RATE LIMIT / QUOTA EXHAUSTED (HTTP 429) ──
                is_429 = (
                    status_code == 429
                    or "429" in err_str
                    or "RESOURCE_EXHAUSTED" in err_str
                    or "quota" in err_str.lower()
                )
                if is_429:
                    logger.warning(
                        f"[RATE LIMIT 429] Gemini quota reached on attempt {attempts}/{max_retries}. "
                        f"Pausing execution for {rate_limit_delay}s before retry..."
                    )
                    if attempts >= max_retries:
                        logger.error(f"[RATE LIMIT 429] Exhausted all {max_retries} attempts due to rate limit: {e}")
                        raise
                    time.sleep(rate_limit_delay)
                    rate_limit_delay *= 1.5
                    continue

                # ── 2. SERVICE UNAVAILABLE / TRANSIENT SERVER ERROR (HTTP 503 / 500) ──
                is_503 = (
                    status_code in (500, 502, 503, 504)
                    or "503" in err_str
                    or "UNAVAILABLE" in err_str
                    or "overloaded" in err_str.lower()
                )
                if is_503:
                    logger.warning(
                        f"[TRANSIENT 503] Gemini service temporarily unavailable on attempt {attempts}/{max_retries}. "
                        f"Retrying in {backoff}s..."
                    )
                    if attempts >= max_retries:
                        logger.error(f"[TRANSIENT 503] Exhausted all {max_retries} attempts due to server unavailability: {e}")
                        raise
                    time.sleep(backoff)
                    backoff *= 2.0
                    continue

                # ── 3. AUTH / CLIENT NON-RETRYABLE ERRORS (HTTP 401, 403, 400) ──
                if status_code in (400, 401, 403) or "API_KEY_INVALID" in err_str:
                    logger.critical(f"[NON-RETRYABLE] Fatal client error {status_code}: {e}")
                    raise

                # ── 4. GENERIC TRANSIENT ERROR FALLBACK ──
                logger.warning(f"Unexpected error during Gemini extraction (Attempt {attempts}/{max_retries}): {e}")
                if attempts >= max_retries:
                    logger.error(f"Exhausted all {max_retries} attempts: {e}")
                    raise
                time.sleep(backoff)
                backoff *= 2.0

        raise RuntimeError("Failed to extract structured content from Gemini after retries.")
