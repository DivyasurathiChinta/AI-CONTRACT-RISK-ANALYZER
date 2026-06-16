"""
services/gemini_service.py
--------------------------
Gemini API integration layer.
"""

import json
import re
import time
from typing import Dict, Any, Optional, List

import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

from app.config import settings
from utils.logger import logger, format_api_error


def _parse_retry_seconds(exc: Exception) -> float:
    """Extract retry delay from Gemini 429 error text when present."""
    match = re.search(r"retry in (\d+(?:\.\d+)?)\s*s", str(exc), re.IGNORECASE)
    if match:
        return min(float(match.group(1)) + 2, 120)
    return settings.gemini_quota_retry_sec


class GeminiService:
    """
    Wrapper around Google's Gemini API with model fallback and rate limiting.
    """

    _last_request_at: float = 0.0

    def __init__(self):
        self._model_candidates: List[str] = settings.gemini_model_candidates()
        self._model_index = 0
        self._configure_api()
        self._load_model(self._model_candidates[0])

    def _configure_api(self) -> None:
        if not settings.validate_gemini_key():
            logger.error("GEMINI_API_KEY missing")
            raise ValueError(
                "GEMINI_API_KEY is missing. "
                "Get a key from https://aistudio.google.com/app/apikey"
            )
        genai.configure(api_key=settings.gemini_api_key)

        self.generation_config = {
            "temperature": 0.1,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
        }

    def _load_model(self, model_name: str) -> None:
        self.model_name = model_name
        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=self.generation_config,
        )
        logger.info("Gemini model loaded: {}", model_name)

    def _throttle(self) -> None:
        """Space out API calls to reduce rate-limit errors during multi-step analysis."""
        delay = settings.gemini_request_delay_sec
        if delay <= 0:
            return
        elapsed = time.time() - GeminiService._last_request_at
        if elapsed < delay:
            time.sleep(delay - elapsed)
        GeminiService._last_request_at = time.time()

    def _switch_to_next_model(self) -> bool:
        if self._model_index >= len(self._model_candidates) - 1:
            return False
        self._model_index += 1
        next_model = self._model_candidates[self._model_index]
        logger.warning(
            "Quota hit on previous model; switching to fallback model: {}",
            next_model,
        )
        self._load_model(next_model)
        return True

    def generate(
        self,
        prompt: str,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ) -> str:
        """Send prompt to Gemini and return text."""
        last_error: Optional[Exception] = None
        models_tried = 0

        while models_tried < len(self._model_candidates):
            for attempt in range(max_retries):
                try:
                    self._throttle()
                    logger.info(
                        "Gemini request model={} attempt {}/{}",
                        self.model_name,
                        attempt + 1,
                        max_retries,
                    )

                    response = self.model.generate_content(prompt)

                    if response is None:
                        raise ValueError("Gemini returned None")

                    if hasattr(response, "text") and response.text:
                        return response.text.strip()

                    if hasattr(response, "candidates") and response.candidates:
                        candidate = response.candidates[0]
                        if hasattr(candidate, "content") and hasattr(
                            candidate.content, "parts"
                        ):
                            parts = candidate.content.parts
                            if parts:
                                text = getattr(parts[0], "text", "")
                                if text:
                                    return text.strip()

                    raise ValueError(
                        "Gemini returned response but no text content."
                    )

                except ResourceExhausted as e:
                    last_error = e
                    wait_time = _parse_retry_seconds(e)
                    logger.warning(
                        "Gemini quota/rate limit (model={}, attempt={}/{}), waiting {:.0f}s",
                        self.model_name,
                        attempt + 1,
                        max_retries,
                        wait_time,
                    )
                    if attempt < max_retries - 1:
                        time.sleep(wait_time)
                        continue
                    break

                except Exception as e:
                    last_error = e
                    logger.exception(
                        "Gemini attempt failed model={} attempt={}/{}",
                        self.model_name,
                        attempt + 1,
                        max_retries,
                    )

                    error_str = str(e).lower()
                    if (
                        "api key" in error_str
                        or "permission" in error_str
                        or "403" in error_str
                        or "not found" in error_str
                        or "404" in error_str
                    ):
                        raise

                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        logger.warning(
                            "Retrying Gemini request in {:.1f} seconds...",
                            wait_time,
                        )
                        time.sleep(wait_time)

            models_tried += 1
            if not self._switch_to_next_model():
                break

        raise RuntimeError(format_api_error(last_error)) from last_error

    def generate_json(
        self,
        prompt: str,
        fallback: Optional[Dict] = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """Generate JSON response."""
        raw_response = self.generate(
            prompt=prompt,
            max_retries=max_retries,
        )

        logger.debug(
            "Gemini JSON response preview: {}",
            raw_response[:500],
        )

        try:
            return json.loads(raw_response.strip())
        except json.JSONDecodeError:
            pass

        code_block_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        matches = re.findall(code_block_pattern, raw_response, re.DOTALL)
        if matches:
            try:
                return json.loads(matches[0].strip())
            except json.JSONDecodeError:
                pass

        json_pattern = r"\{[\s\S]*\}"
        match = re.search(json_pattern, raw_response)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        logger.warning(
            "Failed to parse Gemini JSON. Response preview: {}",
            raw_response[:500],
        )

        if fallback is not None:
            return fallback

        raise ValueError("Failed to parse Gemini JSON response.")


_gemini_service: Optional[GeminiService] = None


def get_gemini_service() -> GeminiService:
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService()
    return _gemini_service


def reset_gemini_service() -> None:
    """Clear cached client (e.g. after .env model change)."""
    global _gemini_service
    _gemini_service = None
