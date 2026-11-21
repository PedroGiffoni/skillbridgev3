from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / '.env',
        env_file_encoding='utf-8', extra='ignore',
    )
    gemini_api_key: SecretStr = SecretStr('')
    gemini_model: str = Field(default='', max_length=120, pattern=r'^[a-zA-Z0-9._/-]*$')
    gemini_free_tier_confirmed: bool = False
    gemini_tts_model: str = Field(default='', max_length=120, pattern=r'^[a-zA-Z0-9._/-]*$')
    gemini_tts_free_tier_confirmed: bool = False
    study_plan_v3_enabled: bool = True
    gemini_timeout_seconds: float = Field(default=30, ge=1, le=60)
    gemini_max_requests_per_minute: int = Field(default=5, ge=1, le=60)
    cors_origins: list[str] = ['http://127.0.0.1:5173', 'http://localhost:5173']

    auth_db_path: Path = Path(__file__).resolve().parents[1] / 'data' / 'skillbridge.sqlite3'
    auth_otp_secret: SecretStr = SecretStr('')
    auth_cookie_secure: bool = False
    auth_admin_emails: list[str] = Field(default_factory=list, max_length=20)
    auth_google_client_id: str = Field(default='', max_length=255)
    auth_smtp_host: str = ''
    auth_smtp_port: int = Field(default=587, ge=1, le=65535)
    auth_smtp_username: str = ''
    auth_smtp_password: SecretStr = SecretStr('')
    auth_smtp_from: str = ''
    auth_smtp_ssl: bool = False
    auth_otp_ttl_seconds: int = Field(default=600, ge=60, le=1800)
    auth_session_ttl_seconds: int = Field(default=60 * 60 * 24 * 7, ge=60, le=60 * 60 * 24 * 30)

    @property
    def ready(self) -> bool:
        return bool(self.gemini_api_key.get_secret_value().strip()
                    and self.gemini_model and self.gemini_free_tier_confirmed)

    @property
    def gemini_tts_ready(self) -> bool:
        return bool(self.gemini_api_key.get_secret_value().strip()
                    and self.gemini_tts_model and self.gemini_tts_free_tier_confirmed)
