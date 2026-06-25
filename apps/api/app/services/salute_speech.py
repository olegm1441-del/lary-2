from uuid import uuid4

import httpx

from app.core.config import settings
from app.services.audio_payload import AudioPayloadError, audio_to_pcm16_16khz


class SaluteSpeechError(Exception):
    def __init__(self, code: str, provider_status: int | None = None, request_id: str | None = None):
        super().__init__(code)
        self.code = code
        self.provider_status = provider_status
        self.request_id = request_id


SUPPORTED_CONTENT_TYPES = {
    "audio/ogg": "audio/ogg;codecs=opus",
    "audio/ogg;codecs=opus": "audio/ogg;codecs=opus",
    "audio/mpeg": "audio/mpeg",
    "audio/mp3": "audio/mpeg",
    "audio/flac": "audio/flac",
    "audio/x-pcm": "audio/x-pcm;bit=16;rate=16000",
    "audio/wav": "audio/x-pcm;bit=16;rate=16000",
    "audio/x-wav": "audio/x-pcm;bit=16;rate=16000",
}


def transcribe_audio(audio: bytes, content_type: str | None) -> str:
    if not settings.salute_speech_authorization_key:
        raise SaluteSpeechError("speech_not_configured")
    if len(audio) > 2 * 1024 * 1024:
        raise SaluteSpeechError("audio_too_large")

    audio_payload, salute_content_type = _prepare_audio_payload(audio, content_type)
    token = _get_access_token()

    response = httpx.post(
        "https://smartspeech.sber.ru/rest/v1/speech:recognize",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": salute_content_type,
            "Accept": "application/json",
        },
        content=audio_payload,
        timeout=60,
        verify=settings.salute_speech_verify_ssl_certs,
    )
    if response.status_code >= 400:
        raise SaluteSpeechError(
            "recognition_failed",
            provider_status=response.status_code,
            request_id=response.headers.get("x-request-id") or response.headers.get("rqtm"),
        )

    return _extract_text(response.json())


def _get_access_token() -> str:
    response = httpx.post(
        "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": str(uuid4()),
            "Authorization": f"Basic {settings.salute_speech_authorization_key}",
        },
        data={"scope": settings.salute_speech_scope},
        timeout=30,
        verify=settings.salute_speech_verify_ssl_certs,
    )
    if response.status_code >= 400:
        raise SaluteSpeechError(
            "token_failed",
            provider_status=response.status_code,
            request_id=response.headers.get("x-request-id") or response.headers.get("rqtm"),
        )
    token = response.json().get("access_token")
    if not token:
        raise SaluteSpeechError("token_missing")
    return token


def _prepare_audio_payload(audio: bytes, content_type: str | None) -> tuple[bytes, str]:
    normalized = (content_type or "").split(";")[0].strip().lower()
    if normalized in {"audio/wav", "audio/x-wav"}:
        try:
            return audio_to_pcm16_16khz(audio, content_type), "audio/x-pcm;bit=16;rate=16000"
        except AudioPayloadError as exc:
            raise SaluteSpeechError("unsupported_audio_format") from exc
    return audio, _normalize_content_type(content_type)


def _normalize_content_type(content_type: str | None) -> str:
    normalized = (content_type or "").split(";")[0].strip().lower()
    if normalized == "audio/ogg" and content_type and "opus" in content_type.lower():
        return "audio/ogg;codecs=opus"
    if normalized in SUPPORTED_CONTENT_TYPES:
        return SUPPORTED_CONTENT_TYPES[normalized]
    raise SaluteSpeechError("unsupported_audio_format")


def _extract_text(payload) -> str:
    candidates: list[str] = []
    if isinstance(payload, dict):
        for key in ("text", "normalized_text", "result"):
            value = payload.get(key)
            if isinstance(value, str):
                candidates.append(value)
        for key in ("results", "hypotheses"):
            value = payload.get(key)
            if isinstance(value, list):
                candidates.extend(_extract_text(item) for item in value)
    elif isinstance(payload, list):
        candidates.extend(_extract_text(item) for item in payload)

    text = " ".join(item.strip() for item in candidates if item and item.strip())
    if not text:
        raise SaluteSpeechError("empty_transcription")
    return text
