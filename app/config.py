import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "SupportGenie AI"
    APP_VERSION: str = "1.0.0"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = True

    # AI & API Configuration
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Business Rules Limits
    AUTO_REFUND_LIMIT: float = 50.0  # Max USD courtesy credit for automated approval
    REFUND_WINDOW_DAYS: int = 180    # Days between courtesy credits (1 per 6 months)
    MAX_REBOOT_ATTEMPTS: int = 2     # Max repeated troubleshooting attempts before escalation
    SIMILARITY_THRESHOLD: float = 0.55 # Minimum retrieval score for grounding

    # Database
    DB_PATH: str = str(BASE_DIR / "supportgenie.db")

settings = Settings()
