from fastapi import APIRouter, HTTPException, Request, Response

from app.core.config import settings
from app.data.modules import get_module, get_modules
from app.schemas.modules import ModuleItem, ModulesResponse, ModuleValidationRequest, ModuleValidationResponse
from app.services.account_store import ModuleAccessError, get_request_context, prepare_module_access, record_module_run_success
from app.services.salary_calculator import SalaryGenerateRequest, SalaryGenerateResponse, SalaryGenerationError, create_salary_run
from app.services.salary_sources.aggregator import probe_salary_sources
from app.services.salary_sources.models import SalaryProbeRequest, SalaryProbeResponse
from app.services.module_validation import validate_module_inputs
from app.services.product_registry import (
    UnknownContestError,
    UnknownModuleError,
    get_product_registry,
)

router = APIRouter(prefix="/api/modules", tags=["Modules"])


@router.get("", response_model=ModulesResponse)
def list_modules():
    if settings.product_registry_runtime_enabled:
        registry = get_product_registry()
        legacy = {item["slug"]: item for item in get_modules()}
        items = []
        for module in registry.get_modules():
            old = legacy.get(module.slug, {})
            items.append(
                ModuleItem(
                    slug=module.slug,
                    status="active" if module.status == "active" else "coming_soon",
                    title=module.title,
                    task_title=module.title,
                    duration=module.duration,
                    competition="",
                    output_formats=module.output_formats,
                    fields=old.get("fields", []),
                    supported_contests=[
                        {"slug": contest.slug, "name": contest.name, "short_name": contest.short_name}
                        for contest in registry.get_supported_contests(module.slug)
                    ],
                )
            )
        return ModulesResponse(items=items)
    return ModulesResponse(items=[ModuleItem(**item) for item in get_modules()])


@router.get("/{module_slug}/profiles/{contest_slug}")
def module_profile(module_slug: str, contest_slug: str):
    try:
        return get_product_registry().public_profile(module_slug, contest_slug)
    except UnknownModuleError as exc:
        raise HTTPException(status_code=404, detail={"message": "Такая задача не найдена."}) from exc
    except UnknownContestError as exc:
        raise HTTPException(status_code=404, detail={"message": "Такой конкурс не найден."}) from exc


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


@router.post("/salary/generate", response_model=SalaryGenerateResponse)
def salary_generate(payload: SalaryGenerateRequest, request: Request, response: Response):
    context = get_request_context(request, response)
    try:
        access = prepare_module_access("salary", context)
    except ModuleAccessError as exc:
        raise HTTPException(status_code=402, detail={"message": str(exc)}) from exc

    try:
        run, generated = create_salary_run(payload)
    except SalaryGenerationError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc), "error_code": exc.error_code}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc

    record_module_run_success(run, access, payload.model_dump())
    return SalaryGenerateResponse(
        **generated.model_dump(),
        status=run.status,
        message="Расчет готов. Можно скачать DOCX или скопировать текст.",
    )


@router.post("/salary/probe-sources", response_model=SalaryProbeResponse)
def salary_probe_sources(payload: SalaryProbeRequest):
    if settings.app_env == "production":
        raise HTTPException(status_code=404, detail={"message": "Такой endpoint недоступен."})
    return probe_salary_sources(payload.role, payload.region, payload.year)
