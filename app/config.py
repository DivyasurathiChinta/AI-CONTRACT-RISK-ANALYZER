"""
app/config.py
-------------
Central configuration management using Pydantic Settings.

WHY THIS PATTERN:
- Single source of truth for all environment variables
- Type validation at startup (catches missing keys immediately)
- Easy to mock in tests
- Interview talking point: "I used the settings pattern to decouple config from business logic"
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Pydantic validates types at startup — if GEMINI_API_KEY is missing,
    the server fails fast with a clear error instead of crashing at runtime.
    """

    # --- Gemini AI Configuration ---
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    gemini_fallback_models: str = os.getenv(
        "GEMINI_FALLBACK_MODELS",
        "gemini-2.0-flash",
    )
    gemini_request_delay_sec: float = float(os.getenv("GEMINI_REQUEST_DELAY_SEC", "3"))
    gemini_quota_retry_sec: float = float(os.getenv("GEMINI_QUOTA_RETRY_SEC", "60"))

    # --- Server Configuration ---
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    debug: bool = os.getenv("DEBUG", "True").lower() == "true"

    # --- File Upload Configuration ---
    max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    upload_dir: str = os.getenv("UPLOAD_DIR", "uploads")

    # --- Application Metadata ---
    app_name: str = os.getenv("APP_NAME", "AI Contract Risk Analyzer")
    app_version: str = os.getenv("APP_VERSION", "1.0.0")

    # --- Frontend ---
    backend_url: str = os.getenv("BACKEND_URL", "http://localhost:8000")

    # --- Uvicorn reload (used by run.py) ---
    api_reload: bool = os.getenv("API_RELOAD", "True").lower() == "true"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"   # Silently ignore any unknown env vars

    @property
    def max_file_size_bytes(self) -> int:
        """Convert MB to bytes for file size validation."""
        return self.max_file_size_mb * 1024 * 1024

    def validate_gemini_key(self) -> bool:
        """Check if Gemini API key is configured."""
        return bool(self.gemini_api_key and self.gemini_api_key != "your_gemini_api_key_here")

    def gemini_model_candidates(self) -> list[str]:
        """Primary model first, then fallbacks (deduplicated)."""
        models = [self.gemini_model.strip()]
        for name in self.gemini_fallback_models.split(","):
            name = name.strip()
            if name and name not in models:
                models.append(name)
        return models


@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings instance.
    
    WHY lru_cache:
    - Settings object is created once and reused across all requests
    - Prevents repeated environment variable reads
    - In tests, you can clear the cache to inject different settings
    """
    return Settings()


# Convenience singleton for direct imports
settings = get_settings()
