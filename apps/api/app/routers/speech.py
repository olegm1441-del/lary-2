from fastapi import APIRouter, HTTPException, UploadFile

from app.core.config import settings
from app.services.salute_speech import SaluteSpeechError, transcribe_audio

router = APIRouter(prefix="/api/speech", tags=["Speech"])


@router.post("/transcribe")
async def transcribe(audio: UploadFile):
    if not settings.salute_speech_authorization_key:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Голосовой ввод временно недоступен. Можно заполнить поле текстом.",
                "code": "speech_not_configured",
            },
        )

    audio_bytes = await audio.read()
    try:
        text = transcribe_audio(audio_bytes, audio.content_type)
    except SaluteSpeechError as exc:
        code = str(exc)
        status_code = 415 if code == "unsupported_audio_format" else 413 if code == "audio_too_large" else 502
        message = "Не получилось распознать голос. Можно заполнить поле текстом."
        if code == "unsupported_audio_format":
            message = "Этот формат аудио не поддерживается. Попробуйте OGG/Opus, MP3, FLAC или WAV."
        if code == "audio_too_large":
            message = "Аудио длиннее допустимого размера. Запишите фрагмент до одной минуты."
        raise HTTPException(status_code=status_code, detail={"message": message, "code": code}) from exc
    return {"text": text}
