from fastapi import APIRouter, HTTPException

from app.schemas.ai import AiTestRequest, AiTestResponse
from app.services.ai_router import AiRouterError, run_ai_test

router = APIRouter(prefix="/api/ai", tags=["AI"])


@router.post("/test", response_model=AiTestResponse)
def ai_test(payload: AiTestRequest):
    try:
        result = run_ai_test(payload.text)
        return AiTestResponse(
            provider="gigachat",
            module="ai_test",
            result=result,
        )
    except AiRouterError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GigaChat request failed: {e}")
