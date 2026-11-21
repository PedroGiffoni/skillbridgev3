"""Short-lived questionnaire integrity. The payload is not encrypted."""
import base64
import hashlib
import hmac
import json
import secrets
import time
import zlib

from .schemas import Questionnaire


class Tokens:
    def __init__(self, key: bytes | None = None):
        self.key = key or secrets.token_bytes(32)

    def sign(self, questionnaire: Questionnaire) -> str:
        payload = json.dumps({'expires': int(time.time()) + 3600, 'nonce': secrets.token_urlsafe(12),
                              'questionnaire': questionnaire.model_dump(exclude={'token'})},
                             ensure_ascii=False, separators=(',', ':')).encode()
        body = base64.urlsafe_b64encode(zlib.compress(payload)).decode()
        if len(body) + 65 > 24000:
            raise ValueError('Questionário excede o limite de tamanho.')
        signature = hmac.new(self.key, body.encode(), hashlib.sha256).hexdigest()
        return f'{body}.{signature}'

    def verify(self, token: str) -> Questionnaire:
        try:
            body, signature = token.rsplit('.', 1)
            expected = hmac.new(self.key, body.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, signature):
                raise ValueError('Invalid signature')
            # Signature is verified first: only this process can produce payloads.
            data = json.loads(zlib.decompress(base64.urlsafe_b64decode(body)))
            if data['expires'] <= time.time():
                raise ValueError('Expired')
            return Questionnaire.model_validate(data['questionnaire'])
        except (ValueError, KeyError, TypeError, zlib.error) as exc:
            raise ValueError('Avaliação expirada ou inválida. Gere um novo questionário.') from exc
