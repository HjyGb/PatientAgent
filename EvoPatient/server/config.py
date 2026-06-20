"""Application configuration via environment variables (pydantic-settings)."""

from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class Settings:
    """Server settings — all values come from environment or sensible defaults."""

    # ── Server ──
    APP_NAME: str = "PatientAgent API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── Database ──
    DATABASE_URL: str = "sqlite+aiosqlite:///./patient_agent.db"

    # ── Auth (JWT) ──
    SECRET_KEY: str = "change-me-in-production-use-a-random-64-char-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # ── CORS ──
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",   # Alternative React port
        "http://127.0.0.1:5173",
    ]

    # ── LLM (read from env via core.api_call) ──
    # No need to duplicate — core.api_call reads os.getenv directly


settings = Settings()
