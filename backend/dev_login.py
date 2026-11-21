"""Run the SkillBridge API on loopback with an isolated test inbox."""

from pathlib import Path
import secrets

import uvicorn

from app.config import Settings
from app.main import create_app

TEST_EMAIL = 'aluno@example.test'
DEV_DATA = Path(__file__).resolve().parent / 'data' / 'login-local'


def create_local_app(data_dir: Path):
    data_dir.mkdir(parents=True, exist_ok=True)
    key_file = data_dir / 'key.txt'
    if not key_file.exists():
        key_file.write_text(secrets.token_urlsafe(48), encoding='ascii')

    def deliver_code(email: str, code: str) -> None:
        if email != TEST_EMAIL:
            raise ValueError('Use the synthetic test address.')
        (data_dir / 'codigo.txt').write_text(code + '\n', encoding='ascii')

    settings = Settings(
        auth_otp_secret=key_file.read_text(encoding='ascii').strip(),
        auth_db_path=data_dir / 'skillbridge.sqlite3',
        auth_cookie_secure=False,
        auth_google_client_id='',
        cors_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
    )
    return create_app(settings, email_sender=deliver_code)


if __name__ == '__main__':
    uvicorn.run(create_local_app(DEV_DATA), host='127.0.0.1', port=8000, access_log=False)
