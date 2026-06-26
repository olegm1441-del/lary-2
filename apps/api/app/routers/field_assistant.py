from fastapi import APIRouter, HTTPException

from app.schemas.field_assistant import FieldAssistantRequest, FieldAssistantResponse
from app.services.field_quality_rules import analyze_field_quality

router = APIRouter(prefix="/api/field-assistant", tags=["Field assistant"])


@router.post("/analyze", response_model=FieldAssistantResponse)
def analyze_field(payload: FieldAssistantRequest):
    try:
        result = analyze_field_quality(payload.module_slug, payload.field_key, payload.value, payload.form_context)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"message": str(exc)}) from exc
    return FieldAssistantResponse(**result)
