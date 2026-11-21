"""Speech rendering for an already validated lesson theme."""

import asyncio
import base64
from binascii import Error as Base64Error
import io
import wave

import httpx
from google import genai
from google.genai import errors, types

from .config import Settings
from .gemini import GenerationFailure, log_failure, provider_failure

SAMPLE_RATE = 24_000
MAX_WAV_BYTES = 12 * 1024 * 1024
MAX_ENCODED_BYTES = 4 * ((MAX_WAV_BYTES + 2) // 3)
MAX_TRANSCRIPT_CHARS = 7_000
NARRATOR_VOICE = 'Kore'
SPEAKERS = {'host': 'Puck', 'expert': 'Kore'}
VOICE_STYLE = {
    'narrator': 'Português do Brasil, dicção nítida e ritmo didático.',
    'host': 'Português do Brasil, curioso e natural, como em uma conversa de podcast.',
    'expert': 'Português do Brasil, claro e cordial, como em uma conversa de podcast.',
}


def _speech_input(turns: list[tuple[str, str]]) -> tuple[list[dict], list[dict] | dict]:
    single = len(turns) == 1 and turns[0][0] == 'narrator'
    podcast = 2 <= len(turns) <= 12 and {speaker for speaker, _ in turns} == SPEAKERS.keys()
    if not (single or podcast) or sum(len(text) for _, text in turns) > MAX_TRANSCRIPT_CHARS:
        raise GenerationFailure('invalid_response')
    if any(not text.strip() for _, text in turns):
        raise GenerationFailure('invalid_response')

    content = []
    for speaker, text in turns:
        annotation = {'type': 'speech_metadata', 'style': VOICE_STYLE[speaker]}
        if podcast:
            annotation['speaker'] = speaker
        content.append({'type': 'text', 'text': text, 'annotations': [annotation]})

    speech_config = (
        {'speakers': [{'speaker': speaker, 'voice': voice} for speaker, voice in SPEAKERS.items()]}
        if podcast else [{'voice': NARRATOR_VOICE}]
    )
    return [{'type': 'user_input', 'content': content}], speech_config


def _read_wav(encoded: str) -> bytes:
    if not isinstance(encoded, str) or not encoded or len(encoded) > MAX_ENCODED_BYTES:
        raise GenerationFailure('invalid_response')
    try:
        data = base64.b64decode(encoded, validate=True)
        if (not 44 <= len(data) <= MAX_WAV_BYTES
                or int.from_bytes(data[4:8], 'little') + 8 != len(data)):
            raise ValueError
        with wave.open(io.BytesIO(data), 'rb') as sound:
            if (sound.getnchannels(), sound.getsampwidth(), sound.getframerate()) != (1, 2, SAMPLE_RATE):
                raise ValueError
            frames = sound.getnframes()
            if not frames:
                raise ValueError
            sound.setpos(frames - 1)
            if len(sound.readframes(1)) != 2:
                raise ValueError
        return data
    except (Base64Error, EOFError, ValueError, wave.Error):
        raise GenerationFailure('invalid_response') from None


class GeminiThemeSpeech:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def synthesize(self, turns: list[tuple[str, str]]) -> bytes:
        if not self.settings.gemini_tts_ready:
            raise GenerationFailure('not_configured')
        speech_input, speech_config = _speech_input(turns)
        timeout = self.settings.gemini_timeout_seconds
        try:
            async with asyncio.timeout(timeout):
                async with genai.Client(
                    api_key=self.settings.gemini_api_key.get_secret_value(),
                    vertexai=False,
                    http_options=types.HttpOptions(
                        api_version='v1beta',
                        timeout=int(timeout * 1000),
                        # google-genai 2.34 rewrites 0 to 1 before Interactions reads the retry count.
                        # A negative count stops both SDK transports after the original request.
                        retry_options=types.HttpRetryOptions(attempts=-1),
                    ),
                ).aio as client:
                    interaction = await client.interactions.create(
                        model=self.settings.gemini_tts_model,
                        input=speech_input,
                        response_format={'type': 'audio', 'mime_type': 'audio/wav', 'sample_rate': SAMPLE_RATE},
                        generation_config={'speech_config': speech_config},
                        store=False,
                        automatic_continuation=False,
                    )
            audio = getattr(interaction, 'output_audio', None)
            if getattr(interaction, 'status', None) != 'completed' or getattr(audio, 'mime_type', None) != 'audio/wav':
                raise GenerationFailure('invalid_response')
            return _read_wav(getattr(audio, 'data', None))
        except GenerationFailure as exc:
            log_failure(exc, 1)
            raise
        except (TimeoutError, httpx.TimeoutException):
            failure = GenerationFailure('timeout')
        except (ValueError, TypeError):
            failure = GenerationFailure('invalid_response')
        except Exception as exc:
            # Interactions 2.34 exposes status_code; the standard SDK exposes code.
            if isinstance(exc.__cause__, httpx.TimeoutException):
                failure = GenerationFailure('timeout')
            else:
                status = exc.code if isinstance(exc, errors.APIError) else getattr(exc, 'status_code', None)
                failure = provider_failure(status) if type(status) is int else GenerationFailure('unavailable')
        log_failure(failure, 1)
        raise failure from None
