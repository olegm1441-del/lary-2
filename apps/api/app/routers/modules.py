from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.data.modules import get_module, get_modules
from app.schemas.modules import ModuleItem, ModulesResponse, ModuleValidationRequest, ModuleValidationResponse
from app.services.salary_sources.aggregator import probe_salary_sources
from app.services.salary_sources.models import SalaryProbeRequest, SalaryProbeResponse
from app.services.module_validation import validate_module_inputs

router = APIRouter(prefix="/api/modules", tags=["Modules"])


@router.get("", response_model=ModulesResponse)
def list_modules():
    return ModulesResponse(items=[ModuleItem(**item) for item in get_modules()])


@router.get("/{slug}/schema", response_model=ModuleItem)
def module_schema(slug: str):
    module = get_module(slug)
    if not module:
        raise HTTPException(status_code=404, detail={"message": "Такой модуль не найден."})
    return ModuleItem(**module)


@router.post("/{slug}/validate-inputs", response_model=ModuleValidationResponse)
def validate_inputs(slug: str, payload: ModuleValidationRequest):
    try:
        result = validate_module_inputs(slug, payload.inputs)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"message": str(exc)}) from exc
    return ModuleValidationResponse(**result)


@router.post("/salary/probe-sources", response_model=SalaryProbeResponse)
def salary_probe_sources(payload: SalaryProbeRequest):
    if settings.app_env == "production":
        raise HTTPException(status_code=404, detail={"message": "Такой endpoint недоступен."})
    return probe_salary_sources(payload.role, payload.region, payload.year)
