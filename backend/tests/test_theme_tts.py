"""Exercise the installed Gemini SDK with an in-process HTTP transport."""

import base64
import io
import json
from types import SimpleNamespace
import wave

import httpx
import pytest
from pydantic import SecretStr

from app import theme_tts
from app.gemini import GenerationFailure
from app.theme_tts import GeminiThemeSpeech


def settings(ready=True):
    return SimpleNamespace(gemini_tts_ready=ready, gemini_tts_model='gemini-3.8-flash-lite-tts',
                           gemini_api_key=SecretStr('offline-test'), gemini_timeout_seconds=2)


def riff(rate=24_000):
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as sound:
        sound.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
        sound.writeframes(b'\x04\x00' * 48)
    return buffer.getvalue()


def response(data):
    return httpx.Response(200, json={
        'status': 'completed',
        'steps': [{'type': 'model_output', 'content': [{
            'type': 'audio', 'mime_type': 'audio/wav', 'data': base64.b64encode(data).decode(),
        }]}],
    })


def patch_transport(monkeypatch, handler):
    real_client = theme_tts.genai.Client

    def fake_client(**kwargs):
        transport = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        kwargs['http_options'] = kwargs['http_options'].model_copy(update={'httpx_async_client': transport})
        return real_client(**kwargs)

    monkeypatch.setattr(theme_tts.genai, 'Client', fake_client)


@pytest.mark.asyncio
@pytest.mark.parametrize('turns', [
    [('narrator', 'Veja como o primeiro resultado é calculado.')],
    [('host', 'Como podemos calcular o resultado?'), ('expert', 'Vamos usar a média.')],
])
async def test_tts_wav_and_speaker_configuration(monkeypatch, turns):
    sent = []

    def transport(request):
        assert request.url.path == '/v1beta/interactions'
        sent.append(json.loads(request.content))
        return response(riff())

    patch_transport(monkeypatch, transport)
    assert await GeminiThemeSpeech(settings()).synthesize(turns) == riff()
    body, = sent
    assert body['store'] is False
    assert body['response_format'] == {'type': 'audio', 'mime_type': 'audio/wav', 'sample_rate': 24000}
    content = body['input'][0]['content']
    assert [part['text'] for part in content] == [text for _, text in turns]
    speech = body['generation_config']['speech_config']
    if len(turns) == 1:
        assert speech == [{'voice': 'Kore'}]
        assert 'speaker' not in content[0]['annotations'][0]
    else:
        assert {voice['voice'] for voice in speech['speakers']} == {'Kore', 'Puck'}
        assert [part['annotations'][0]['speaker'] for part in content] == ['host', 'expert']


@pytest.mark.asyncio
@pytest.mark.parametrize('status,reason', [(429, 'quota'), (503, 'unavailable'), (400, 'configuration')])
async def test_tts_classifies_error_without_repeating_request(monkeypatch, status, reason):
    sent = []

    def transport(request):
        sent.append(request)
        return httpx.Response(status, json={'error': {'message': 'Texto do provedor que deve ficar privado.'}})

    patch_transport(monkeypatch, transport)
    with pytest.raises(GenerationFailure) as exc:
        await GeminiThemeSpeech(settings()).synthesize([('narrator', 'Texto para narração.')])
    assert exc.value.reason == reason
    assert exc.value.provider_status == status
    assert len(sent) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('data', [b'invalid-wave', riff(16000), riff()[:-2]])
async def test_tts_rejects_invalid_wav(monkeypatch, data):
    patch_transport(monkeypatch, lambda _: response(data))
    with pytest.raises(GenerationFailure) as exc:
        await GeminiThemeSpeech(settings()).synthesize([('narrator', 'Texto para narração.')])
    assert exc.value.reason == 'invalid_response'


@pytest.mark.asyncio
async def test_tts_timeout_and_free_tier_gate(monkeypatch):
    sent = []

    def transport(request):
        sent.append(request)
        raise httpx.ReadTimeout('Atraso do provedor', request=request)

    patch_transport(monkeypatch, transport)
    with pytest.raises(GenerationFailure) as exc:
        await GeminiThemeSpeech(settings(False)).synthesize([('narrator', 'Texto para narração.')])
    assert exc.value.reason == 'not_configured'
    assert not sent
    with pytest.raises(GenerationFailure) as exc:
        await GeminiThemeSpeech(settings()).synthesize([('narrator', 'Texto para narração.')])
    assert exc.value.reason == 'timeout'
    assert len(sent) == 1
