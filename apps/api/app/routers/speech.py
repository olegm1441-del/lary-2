import logging

from fastapi import APIRouter, HTTPException, UploadFile

from app.services.speech_service import SpeechServiceError, transcribe_speech

router = APIRouter(prefix="/api/speech", tags=["Speech"])
logger = logging.getLogger("lary.speech")


@router.post("/transcribe")
async def transcribe(audio: UploadFile):
    audio_bytes = await audio.read()
    try:
        text = transcribe_speech(audio_bytes, audio.content_type)
    except SpeechServiceError as exc:
        code = exc.code
        logger.warning(
            "speech_transcription_failed provider=%s code=%s provider_status=%s request_id=%s content_type=%s file_size=%s",
            exc.provider,
            code,
            exc.provider_status,
            exc.request_id,
            audio.content_type,
            len(audio_bytes),
        )
        status_code = (
            415
            if code == "unsupported_audio_format"
            else 413
            if code == "audio_too_large"
            else 503
            if code in {"speech_not_configured", "vosk_model_missing", "vosk_not_installed"}
            else 502
        )
        message = "Не получилось распознать голос. Можно заполнить поле текстом."
        if code == "unsupported_audio_format":
            message = "Этот формат аудио не поддерживается. Попробуйте записать голос еще раз или заполните поле текстом."
        if code == "audio_too_large":
            message = "Аудио длиннее допустимого размера. Запишите фрагмент до одной минуты."
        if code == "speech_not_configured":
            message = "Голосовой ввод временно недоступен. Можно заполнить поле текстом."
        if code in {"vosk_model_missing", "vosk_not_installed"}:
            message = "Голосовой ввод временно недоступен: модель распознавания не подключена."
        raise HTTPException(status_code=status_code, detail={"message": message, "code": code}) from exc
    return {"text": text}
