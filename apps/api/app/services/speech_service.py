from app.core.config import settings
from app.services.salute_speech import SaluteSpeechError, transcribe_audio
from app.services.vosk_speech import VoskSpeechError, transcribe_with_vosk


class SpeechServiceError(Exception):
    def __init__(self, code: str, provider: str, provider_status: int | None = None, request_id: str | None = None):
        super().__init__(code)
        self.code = code
        self.provider = provider
        self.provider_status = provider_status
        self.request_id = request_id


def transcribe_speech(audio: bytes, content_type: str | None) -> str:
    provider = settings.speech_provider
    if provider == "vosk":
        return _transcribe_vosk(audio, content_type)
    if provider == "salute_then_vosk":
        try:
            return _transcribe_salute(audio, content_type)
        except SpeechServiceError as exc:
            if exc.code in {"recognition_failed", "token_failed"}:
                return _transcribe_vosk(audio, content_type)
            raise
    return _transcribe_salute(audio, content_type)


def _transcribe_salute(audio: bytes, content_type: str | None) -> str:
    try:
        return transcribe_audio(audio, content_type)
    except SaluteSpeechError as exc:
        raise SpeechServiceError(exc.code, "salute", exc.provider_status, exc.request_id) from exc


def _transcribe_vosk(audio: bytes, content_type: str | None) -> str:
    try:
        return transcribe_with_vosk(audio, content_type)
    except VoskSpeechError as exc:
        raise SpeechServiceError(exc.code, "vosk") from exc
