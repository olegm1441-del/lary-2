from uuid import uuid4

import httpx

from app.core.config import settings


class SaluteSpeechError(Exception):
    pass


SUPPORTED_CONTENT_TYPES = {
    "audio/ogg": "audio/ogg;codecs=opus",
    "audio/ogg;codecs=opus": "audio/ogg;codecs=opus",
    "audio/mpeg": "audio/mpeg",
    "audio/mp3": "audio/mpeg",
    "audio/flac": "audio/flac",
    "audio/wav": "audio/x-pcm;bit=16;rate=16000",
    "audio/x-wav": "audio/x-pcm;bit=16;rate=16000",
    "audio/x-pcm": "audio/x-pcm;bit=16;rate=16000",
}


def transcribe_audio(audio: bytes, content_type: str | None) -> str:
    if not settings.salute_speech_authorization_key:
        raise SaluteSpeechError("speech_not_configured")
    if len(audio) > 2 * 1024 * 1024:
        raise SaluteSpeechError("audio_too_large")

    salute_content_type = _normalize_content_type(content_type)
    token = _get_access_token()

    response = httpx.post(
        "https://smartspeech.sber.ru/rest/v1/speech:recognize",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": salute_content_type,
            "Accept": "application/json",
        },
        content=audio,
        timeout=60,
        verify=settings.salute_speech_verify_ssl_certs,
    )
    if response.status_code >= 400:
        raise SaluteSpeechError(f"recognition_failed:{response.status_code}")

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
        raise SaluteSpeechError(f"token_failed:{response.status_code}")
    token = response.json().get("access_token")
    if not token:
        raise SaluteSpeechError("token_missing")
    return token


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
