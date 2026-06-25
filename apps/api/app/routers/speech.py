from fastapi import APIRouter, HTTPException, UploadFile

from app.core.config import settings

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

    await audio.read()
    raise HTTPException(
        status_code=501,
        detail={
            "message": "Ключ SaluteSpeech найден, но прямое распознавание еще не включено в этот MVP-срез.",
            "code": "speech_provider_not_implemented",
        },
    )
