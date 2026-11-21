import base64
from io import BytesIO
from time import time
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from app.main import create_app
from test_api import Fake, settings


def test_email_code_is_single_use_and_session_controls_profile(tmp_path):
    sent = {}
    app = create_app(settings(auth_db_path=tmp_path / 'account.sqlite3'), Fake(),
                     email_sender=sent.__setitem__)
    with TestClient(app) as client:
        assert client.get('/api/account').status_code == 401
        email = 'student@example.com'
        assert client.post('/api/auth/email/request', json={'email': email}).status_code == 204
        assert client.post('/api/auth/email/request', json={'email': email}).status_code == 429
        verify = {'email': email, 'code': sent[email]}
        wrong = {'email': email, 'code': '000000' if sent[email] != '000000' else '000001'}
        assert client.post('/api/auth/email/verify', json=wrong).status_code == 400
        login = client.post('/api/auth/email/verify', json=verify)
        assert login.status_code == 200
        assert 'HttpOnly' in login.headers['set-cookie']
        assert 'SameSite=lax' in login.headers['set-cookie']
        assert client.post('/api/auth/email/verify', json=verify).status_code == 400
        assert client.post('/api/account/profile', json={'photo': 'data:image/svg+xml,<svg>'}).status_code == 422
        profile = client.post('/api/account/profile', json={'display_name': ' Ana  ', 'semester': 2}).json()
        assert profile['display_name'] == 'Ana'
        invalid = 'data:image/jpeg;base64,' + base64.b64encode(b'\xff\xd8\xffbad\xff\xd9').decode()
        assert client.post('/api/account/profile', json={'photo': invalid}).status_code == 422
        jpeg = BytesIO()
        Image.new('RGB', (16, 16), 'purple').save(jpeg, format='JPEG', comment=b'private test metadata')
        photo = 'data:image/jpeg;base64,' + base64.b64encode(jpeg.getvalue()).decode()
        result = client.post('/api/account/profile', json={'photo': photo, 'semester': 2})
        assert result.status_code == 200
        stored = client.get('/api/account').json()
        assert stored['semester'] == 2
        assert b'private test metadata' not in base64.b64decode(stored['photo'].split(',', 1)[1])
        assert client.post('/api/account/profile', json={'photo': None}).json()['photo'] is None
        assert client.post('/api/account/profile', json={'course': 'TI'},
                           headers={'Origin': 'https://other.example'}).status_code == 403
        assert client.post('/api/auth/logout').status_code == 204
        assert client.get('/api/account').status_code == 401


def test_google_sign_in_and_confirmed_email_share_one_profile(tmp_path):
    sent = {}
    claims = {'sub': 'google-student', 'email': 'student@example.com', 'email_verified': True}
    config = settings(auth_db_path=tmp_path / 'account.sqlite3', auth_google_client_id='offline.apps.googleusercontent.com')
    app = create_app(config, Fake(), email_sender=sent.__setitem__, google_verifier=lambda _: claims)
    email = claims['email']
    with TestClient(app) as client:
        assert client.post('/api/auth/google', json={'credential': 'offline-token'}).status_code == 401
        assert client.post('/api/auth/email/request', json={'email': email}).status_code == 204
        assert client.post('/api/auth/email/verify', json={'email': email, 'code': sent[email]}).status_code == 200
        assert client.post('/api/account/profile', json={'display_name': 'Meu perfil'}).status_code == 200
        assert client.post('/api/auth/logout').status_code == 204
        claims['nonce'] = client.get('/api/auth/google/nonce').json()['nonce']
        link = client.post('/api/auth/google', json={'credential': 'offline-token'})
        assert link.status_code == 200
        assert link.json()['email'] == email
        assert client.get('/api/account').status_code == 401
        # The previous code was consumed, and a Google link doesn't turn it into a valid code.
        assert client.post('/api/auth/email/verify', json={'email': email, 'code': sent[email],
                           'link_token': link.json()['link_token']}).status_code == 400
        import app.auth
        with patch.object(app.auth, 'time', lambda: time() + 61):
            assert client.post('/api/auth/email/request', json={'email': email}).status_code == 204
            response = client.post('/api/auth/email/verify', json={'email': email, 'code': sent[email],
                                   'link_token': link.json()['link_token']})
            assert response.status_code == 200
            assert response.json()['display_name'] == 'Meu perfil'
        assert client.post('/api/auth/logout').status_code == 204
        claims['nonce'] = client.get('/api/auth/google/nonce').json()['nonce']
        assert client.post('/api/auth/google', json={'credential': 'offline-token'}).json()['profile']['display_name'] == 'Meu perfil'


def test_new_google_account_is_created_without_signup(tmp_path):
    claims = {'sub': 'another-student', 'email': 'ana@gmail.com', 'email_verified': True}
    config = settings(auth_db_path=tmp_path / 'account.sqlite3', auth_google_client_id='offline.apps.googleusercontent.com')
    app = create_app(config, Fake(), google_verifier=lambda _: claims)
    with TestClient(app) as client:
        claims['nonce'] = client.get('/api/auth/google/nonce').json()['nonce']
        profile = client.post('/api/auth/google', json={'credential': 'offline-token'})
        assert profile.status_code == 200
        assert profile.json()['profile']['email'] == 'ana@gmail.com'
        assert client.get('/api/account').status_code == 200
        assert client.post('/api/auth/google', json={'credential': 'offline-token'}).status_code == 401
