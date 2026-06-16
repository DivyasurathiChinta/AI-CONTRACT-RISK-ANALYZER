"""
utils/logger.py
---------------
Centralized structured logging using Loguru.

WHY LOGURU over standard logging:
- Cleaner API (no need to get logger instances everywhere)
- Automatic formatting with colors in terminal
- Built-in file rotation
- Structured JSON logging ready for production log aggregators (Datadog, CloudWatch)
- Interview talking point: "I used structured logging so logs can be queried programmatically"
"""

import sys

from loguru import logger


def setup_logger(log_level: str = "INFO", log_file: str = "logs/app.log") -> None:
    """
    Configure Loguru logger with:
    - Console output (colored, human readable)
    - File output (structured, with rotation)
    """
    # Remove default handler
    logger.remove()

    # Console handler — human readable with colors
    logger.add(
        sys.stdout,
        level=log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # File handler — structured for production log aggregators
    logger.add(
        log_file,
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
        rotation="10 MB",       # Create new file after 10MB
        retention="7 days",     # Keep logs for 7 days
        compression="zip",      # Compress old logs
        enqueue=True,           # Thread-safe async logging
    )

    logger.info("Logger initialized successfully")


def format_api_error(exc: BaseException) -> str:
    """
    Map exceptions to user-facing messages.
    Gemini/grpc errors often contain `{description: ...}` text that must not
    be embedded in Loguru format strings (Loguru uses str.format on messages).
    """
    from google.api_core.exceptions import ResourceExhausted

    if isinstance(exc, ResourceExhausted) or "429" in str(exc) or "quota" in str(exc).lower():
        return (
            "Gemini API quota exceeded for all configured models. "
            "Wait 1–2 minutes and retry, create a new API key at "
            "https://aistudio.google.com/app/apikey, or set GEMINI_MODEL to "
            "gemini-1.5-flash / gemini-2.5-flash in .env and restart the server."
        )

    if "api key" in str(exc).lower() or "403" in str(exc):
        return (
            "Gemini API key is invalid or lacks permission. "
            "Check GEMINI_API_KEY in your .env file."
        )

    return str(exc)


# Initialize logger on import
setup_logger()

# Re-export for convenience: from utils.logger import logger
__all__ = ["logger", "format_api_error"]
