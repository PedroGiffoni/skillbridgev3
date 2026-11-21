"""Passwordless email and Google login for the SkillBridge account."""
from collections.abc import Mapping
from email.message import EmailMessage
from functools import partial
from hashlib import sha256
from io import BytesIO
import base64
import hmac
import re
import secrets
import smtplib
import ssl
from time import time
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from google.auth.exceptions import GoogleAuthError, TransportError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .accounts import AccountStore
from .config import Settings

SESSION_COOKIE = 'skillbridge_session'
GOOGLE_COOKIE = 'skillbridge_google'
GOOGLE_PATH = '/api/auth/google'
PHOTO_PREFIX = 'data:image/jpeg;base64,'
EMAIL_PATTERN = re.compile(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)+", re.ASCII)


def normalize_email(value: str) -> str:
    value = value.strip().lower()
    if len(value) > 254 or not EMAIL_PATTERN.fullmatch(value):
        raise ValueError('E-mail inválido.')
    return value


def digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()


class Payload(BaseModel):
    model_config = ConfigDict(extra='forbid')


class EmailRequest(Payload):
    email: str
    link_account: bool = False

    @field_validator('email')
    @classmethod
    def valid_email(cls, value: str) -> str:
        return normalize_email(value)


class EmailVerify(EmailRequest):
    code: str = Field(pattern=r'^[0-9]{6}$')
    link_token: str | None = Field(default=None, max_length=100)


class GoogleLogin(Payload):
    credential: str = Field(min_length=1, max_length=8192)


class ProfileFields(Payload):
    display_name: str = Field(default='', max_length=80)
    photo: str | None = Field(default=None, max_length=55_000)
    course: str = Field(default='', max_length=100)
    semester: int | None = Field(default=None, strict=True, ge=1, le=20)
    goal: str = Field(default='', max_length=240)

    @field_validator('display_name', 'course', 'goal')
    @classmethod
    def clean_text(cls, value: str) -> str:
        return ' '.join(value.split())

class EditableProfile(ProfileFields):
    @field_validator('photo')
    @classmethod
    def validate_photo(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            if not value.startswith(PHOTO_PREFIX):
                raise ValueError()
            raw = base64.b64decode(value[len(PHOTO_PREFIX):], validate=True)
            if len(raw) > 40 * 1024:
                raise ValueError()
            normalized = BytesIO()
            with Image.open(BytesIO(raw), formats=['JPEG']) as photo:
                if not (1 <= photo.width <= 256 and 1 <= photo.height <= 256):
                    raise ValueError()
                with photo.convert('RGB') as clean:
                    clean.info.clear()
                    clean.save(normalized, format='JPEG', quality=80, optimize=True)
            if normalized.tell() > 40 * 1024:
                raise ValueError()
        except (ValueError, OSError, Image.DecompressionBombError):
            raise ValueError('Envie uma foto JPEG válida de até 256 × 256 pixels e 40 KiB.') from None
        return PHOTO_PREFIX + base64.b64encode(normalized.getvalue()).decode('ascii')


class AccountProfile(ProfileFields):
    email: str | None


class AuthService:
    def __init__(self, settings: Settings, email_sender, google_verifier):
        self.settings = settings
        self.store = AccountStore(settings.auth_db_path)
        self._sender = email_sender
        self._verifier = google_verifier
        self._secret = settings.auth_otp_secret.get_secret_value().encode()
        self.email_enabled = len(self._secret) >= 32 and bool(
            email_sender or (settings.auth_smtp_host and settings.auth_smtp_from)
        )
        self.google_client_id = settings.auth_google_client_id.strip() if len(self._secret) >= 32 else ''

    def origin(self, request: Request) -> None:
        origin = request.headers.get('origin')
        if origin and origin not in self.settings.cors_origins:
            raise HTTPException(403, 'Origem da solicitação inválida.')

    def require_account(self, request: Request) -> str:
        if request.method not in {'GET', 'HEAD'}:
            self.origin(request)
        token = request.cookies.get(SESSION_COOKIE, '')
        if len(token) == 43:
            with self.store.connect() as db:
                row = db.execute('SELECT account_id FROM auth_sessions WHERE digest = ? AND expires_at > ?',
                                 (digest(token), time())).fetchone()
            if row:
                return row['account_id']
        raise HTTPException(401, 'Entre na sua conta para continuar.')

    def cookie(self, response: Response, name: str, value: str, path: str, max_age: int):
        response.set_cookie(name, value, path=path, httponly=True, samesite='lax',
                            secure=self.settings.auth_cookie_secure, max_age=max_age)

    def clear(self, response: Response, name: str, path: str):
        response.delete_cookie(name, path=path, httponly=True, samesite='lax',
                               secure=self.settings.auth_cookie_secure)

    def session(self, request: Request, response: Response, account_id: str) -> AccountProfile:
        token = secrets.token_urlsafe(32)
        now = time()
        old_token = request.cookies.get(SESSION_COOKIE, '')
        ttl = self.settings.auth_session_ttl_seconds
        with self.store.connect(write=True) as db:
            db.execute('DELETE FROM auth_sessions WHERE expires_at <= ?', (now,))
            if len(old_token) == 43:
                db.execute('DELETE FROM auth_sessions WHERE digest = ?', (digest(old_token),))
            db.execute('INSERT INTO auth_sessions VALUES (?, ?, ?)', (digest(token), account_id, now + ttl))
        self.cookie(response, SESSION_COOKIE, token, '/api', ttl)
        return self.profile(account_id)

    def profile(self, account_id: str) -> AccountProfile:
        with self.store.connect() as db:
            row = db.execute(
                'SELECT email, display_name, photo, course, semester, goal FROM accounts WHERE id = ?',
                (account_id,),
            ).fetchone()
        if row is None:
            raise HTTPException(401, 'Entre na sua conta para continuar.')
        return AccountProfile(**dict(row))

    def hash_code(self, email: str, scope: str, code: str) -> str:
        return hmac.new(self._secret, f'{scope}\0{email}\0{code}'.encode(), 'sha256').hexdigest()

    def send_code(self, email: str, code: str) -> None:
        if self._sender:
            self._sender(email, code)
            return
        settings = self.settings
        message = EmailMessage()
        message['To'] = email
        message['From'] = settings.auth_smtp_from
        message['Subject'] = 'Seu código do SkillBridge'
        message.set_content(f'Seu código de acesso ao SkillBridge é {code}.\n'
                            'Digite-o na tela de acesso. O código expira e funciona uma única vez.')
        tls = ssl.create_default_context()
        host, port = settings.auth_smtp_host, settings.auth_smtp_port
        connection = (smtplib.SMTP_SSL(host, port, timeout=12, context=tls)
                      if settings.auth_smtp_ssl else smtplib.SMTP(host, port, timeout=12))
        with connection as smtp:
            if not settings.auth_smtp_ssl:
                smtp.starttls(context=tls)
            if settings.auth_smtp_username:
                smtp.login(settings.auth_smtp_username, settings.auth_smtp_password.get_secret_value())
            smtp.send_message(message)

    def email_scope(self, data: EmailRequest, request: Request) -> str:
        if data.link_account:
            return self.require_account(request)
        return 'login'

    def request_code(self, data: EmailRequest, request: Request):
        self.origin(request)
        if not self.email_enabled:
            raise HTTPException(503, 'O acesso por e-mail está indisponível no momento.')
        scope, now = self.email_scope(data, request), time()
        code = f'{secrets.randbelow(1_000_000):06d}'
        with self.store.connect(write=True) as db:
            db.execute('DELETE FROM auth_codes WHERE expires_at <= ?', (now,))
            sent = db.execute('SELECT COUNT(*) FROM auth_codes WHERE issued_at > ?', (now - 60,)).fetchone()[0]
            row = db.execute('SELECT MAX(issued_at) FROM auth_codes WHERE email = ?', (data.email,)).fetchone()
            if sent >= 30 or (row[0] is not None and now - row[0] < 60):
                raise HTTPException(429, 'Aguarde um minuto para pedir outro código.', headers={'Retry-After': '60'})
            db.execute("""
                INSERT INTO auth_codes (email, scope, digest, issued_at, expires_at, remaining) VALUES (?, ?, ?, ?, ?, 5)
                ON CONFLICT(email, scope) DO UPDATE SET digest = excluded.digest, issued_at = excluded.issued_at,
                    expires_at = excluded.expires_at, remaining = 5
            """, (data.email, scope, self.hash_code(data.email, scope, code), now, now + self.settings.auth_otp_ttl_seconds))
        try:
            self.send_code(data.email, code)
        except (smtplib.SMTPException, OSError, ValueError):
            raise HTTPException(503, 'Não foi possível enviar o código. Aguarde um minuto antes de pedir outro.') from None
        return Response(status_code=204)

    def verify_code(self, data: EmailVerify, request: Request, response: Response) -> AccountProfile:
        self.origin(request)
        if not self.email_enabled:
            raise HTTPException(503, 'O acesso por e-mail está indisponível no momento.')
        if data.link_token and data.link_account:
            raise HTTPException(422, 'Escolha uma forma de vincular a conta.')
        scope, now = self.email_scope(data, request), time()
        with self.store.connect(write=True) as db:
            row = db.execute('SELECT * FROM auth_codes WHERE email = ? AND scope = ?', (data.email, scope)).fetchone()
            active = row is not None and row['expires_at'] > now and row['remaining'] > 0
            valid = active and hmac.compare_digest(row['digest'], self.hash_code(data.email, scope, data.code))
            if active:
                db.execute('UPDATE auth_codes SET remaining = ? WHERE email = ? AND scope = ?',
                           (0 if valid else row['remaining'] - 1, data.email, scope))
        if not valid:
            raise HTTPException(400, 'Código incorreto ou expirado. Confira o código ou solicite outro.')
        with self.store.connect(write=True) as db:
            existing = db.execute('SELECT id, google_sub FROM accounts WHERE email = ?', (data.email,)).fetchone()
            if data.link_account:
                if existing and existing['id'] != scope:
                    raise HTTPException(409, 'Esse e-mail já está vinculado a outra conta.')
                db.execute('UPDATE accounts SET email = ? WHERE id = ?', (data.email, scope))
                account_id = scope
            elif data.link_token:
                proof_key = digest(data.link_token)
                proof = db.execute("""
                    SELECT google_sub FROM auth_google_proofs WHERE digest = ? AND email = ?
                        AND expires_at > ? AND google_sub IS NOT NULL
                """, (proof_key, data.email, now)).fetchone()
                if not proof or not existing:
                    raise HTTPException(409, 'A confirmação do Google expirou. Tente entrar com Google novamente.')
                linked = db.execute('SELECT id FROM accounts WHERE google_sub = ?', (proof['google_sub'],)).fetchone()
                if (linked and linked['id'] != existing['id']) or existing['google_sub'] not in (None, proof['google_sub']):
                    raise HTTPException(409, 'A conta já possui outro acesso Google.')
                account_id = existing['id']
                db.execute('UPDATE accounts SET google_sub = ? WHERE id = ?', (proof['google_sub'], account_id))
                db.execute('DELETE FROM auth_google_proofs WHERE digest = ?', (proof_key,))
            elif existing:
                account_id = existing['id']
            else:
                account_id = uuid4().hex
                db.execute('INSERT INTO accounts (id, email) VALUES (?, ?)', (account_id, data.email))
        return self.session(request, response, account_id)

    def google_nonce(self, request: Request, response: Response):
        self.origin(request)
        if not self.google_client_id:
            raise HTTPException(503, 'O acesso com Google está indisponível no momento.')
        token, nonce, now = secrets.token_urlsafe(32), secrets.token_urlsafe(24), time()
        with self.store.connect(write=True) as db:
            db.execute('DELETE FROM auth_google_proofs WHERE expires_at <= ?', (now,))
            previous = request.cookies.get(GOOGLE_COOKIE, '')
            if len(previous) == 43:
                db.execute('DELETE FROM auth_google_proofs WHERE digest = ? AND nonce IS NOT NULL', (digest(previous),))
            if db.execute('SELECT COUNT(*) FROM auth_google_proofs WHERE nonce IS NOT NULL').fetchone()[0] >= 300:
                raise HTTPException(429, 'Aguarde um momento e tente entrar com Google novamente.')
            db.execute('INSERT INTO auth_google_proofs (digest, nonce, expires_at) VALUES (?, ?, ?)',
                       (digest(token), nonce, now + 300))
        self.cookie(response, GOOGLE_COOKIE, token, GOOGLE_PATH, 300)
        return {'nonce': nonce}

    def google_login(self, data: GoogleLogin, request: Request, response: Response):
        self.origin(request)
        if not self.google_client_id:
            raise HTTPException(503, 'O acesso com Google está indisponível no momento.')
        challenge = request.cookies.get(GOOGLE_COOKIE, '')
        if len(challenge) != 43:
            raise HTTPException(401, 'A sessão do Google expirou. Tente novamente.')
        now, challenge_key = time(), digest(challenge)
        with self.store.connect(write=True) as db:
            proof = db.execute(
                'SELECT nonce FROM auth_google_proofs WHERE digest = ? AND nonce IS NOT NULL AND expires_at > ?',
                (challenge_key, now),
            ).fetchone()
            db.execute('DELETE FROM auth_google_proofs WHERE digest = ? AND nonce IS NOT NULL', (challenge_key,))
        if proof is None:
            raise HTTPException(401, 'A sessão do Google expirou. Tente novamente.')
        try:
            claims = (self._verifier(data.credential) if self._verifier else
                      id_token.verify_oauth2_token(data.credential, partial(GoogleRequest(), timeout=8), self.google_client_id))
            if not isinstance(claims, Mapping) or claims.get('nonce') != proof['nonce']:
                raise ValueError()
            subject = claims['sub']
            if not isinstance(subject, str) or not 1 <= len(subject) <= 255 or claims.get('email_verified') is not True:
                raise ValueError()
            email = normalize_email(claims['email'])
        except TransportError:
            raise HTTPException(503, 'O Google está indisponível. Tente novamente.') from None
        except (GoogleAuthError, ValueError, KeyError, TypeError, AttributeError):
            raise HTTPException(401, 'Não foi possível confirmar a entrada com Google.') from None
        self.clear(response, GOOGLE_COOKIE, GOOGLE_PATH)
        trusted_email = email.endswith('@gmail.com') or bool(claims.get('hd'))
        with self.store.connect(write=True) as db:
            existing = db.execute('SELECT id FROM accounts WHERE google_sub = ?', (subject,)).fetchone()
            if existing:
                account_id = existing['id']
            elif db.execute('SELECT 1 FROM accounts WHERE email = ?', (email,)).fetchone():
                if not self.email_enabled:
                    raise HTTPException(503, 'Confirme a vinculação quando o envio de código por e-mail estiver disponível.')
                link_token = secrets.token_urlsafe(32)
                db.execute("""
                    INSERT INTO auth_google_proofs (digest, google_sub, email, expires_at) VALUES (?, ?, ?, ?)
                """, (digest(link_token), subject, email, now + 600))
                return {'email': email, 'link_token': link_token}
            else:
                account_id = uuid4().hex
                db.execute('INSERT INTO accounts (id, email, google_sub) VALUES (?, ?, ?)',
                           (account_id, email if trusted_email else None, subject))
        return {'profile': self.session(request, response, account_id)}

    def update_profile(self, data: EditableProfile, account_id: str) -> AccountProfile:
        with self.store.connect(write=True) as db:
            db.execute('UPDATE accounts SET display_name = ?, photo = ?, course = ?, semester = ?, goal = ? WHERE id = ?',
                       (data.display_name, data.photo, data.course, data.semester, data.goal, account_id))
        return self.profile(account_id)

    def logout(self, request: Request) -> Response:
        self.origin(request)
        token = request.cookies.get(SESSION_COOKIE, '')
        if len(token) == 43:
            with self.store.connect(write=True) as db:
                db.execute('DELETE FROM auth_sessions WHERE digest = ?', (digest(token),))
        response = Response(status_code=204)
        self.clear(response, SESSION_COOKIE, '/api')
        return response


def install_auth(app: FastAPI, settings: Settings, *, email_sender=None, google_verifier=None) -> AuthService:
    auth = AuthService(settings, email_sender, google_verifier)

    @app.get('/api/auth/config')
    def auth_config():
        return {'email_enabled': auth.email_enabled, 'google_client_id': auth.google_client_id or None}

    app.add_api_route('/api/auth/email/request', auth.request_code, methods=['POST'], status_code=204,
                      response_class=Response)
    app.add_api_route('/api/auth/email/verify', auth.verify_code, methods=['POST'], response_model=AccountProfile)
    app.add_api_route('/api/auth/google/nonce', auth.google_nonce, methods=['GET'])
    app.add_api_route('/api/auth/google', auth.google_login, methods=['POST'])
    app.add_api_route('/api/auth/logout', auth.logout, methods=['POST'], status_code=204, response_class=Response)

    @app.get('/api/account', response_model=AccountProfile)
    def account(account_id: str = Depends(auth.require_account)):
        return auth.profile(account_id)

    @app.post('/api/account/profile', response_model=AccountProfile)
    def update_profile(data: EditableProfile, account_id: str = Depends(auth.require_account)):
        return auth.update_profile(data, account_id)

    return auth
