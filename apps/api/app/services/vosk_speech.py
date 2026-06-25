import json
from pathlib import Path

from app.core.config import settings
from app.services.audio_payload import AudioPayloadError, audio_to_pcm16_16khz


class VoskSpeechError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


_cached_model = None
_cached_model_path: str | None = None


def transcribe_with_vosk(audio: bytes, content_type: str | None) -> str:
    if not settings.vosk_model_path:
        raise VoskSpeechError("vosk_model_missing")

    model_path = Path(settings.vosk_model_path)
    if not model_path.exists():
        raise VoskSpeechError("vosk_model_missing")

    try:
        pcm = audio_to_pcm16_16khz(audio, content_type)
    except AudioPayloadError as exc:
        raise VoskSpeechError("unsupported_audio_format") from exc

    try:
        from vosk import KaldiRecognizer
    except ImportError as exc:
        raise VoskSpeechError("vosk_not_installed") from exc

    recognizer = KaldiRecognizer(_get_model(str(model_path)), 16000)
    recognizer.AcceptWaveform(pcm)
    payload = json.loads(recognizer.FinalResult())
    text = str(payload.get("text") or "").strip()
    if not text:
        raise VoskSpeechError("empty_transcription")
    return text


def _get_model(model_path: str):
    global _cached_model, _cached_model_path
    if _cached_model is not None and _cached_model_path == model_path:
        return _cached_model

    from vosk import Model

    _cached_model = Model(model_path)
    _cached_model_path = model_path
    return _cached_model
