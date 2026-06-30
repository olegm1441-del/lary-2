from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse

from app.core.config import settings
from app.schemas.modules import EmailFileRequest, EmailFileResponse, ImproveRequest, ModuleRunCreateRequest, ModuleRunCreateResponse, ModuleRunResultResponse
from app.services.module_engine import create_module_run, improve_run
from app.services.file_generators import generate_docx, generate_pdf, generate_pptx
from app.services.account_store import ModuleAccessError, get_request_context, load_persisted_run, prepare_module_access, record_module_run_success, save_result_for_email
from app.services.run_store import run_store

router = APIRouter(prefix="/api/module-runs", tags=["Module runs"])

MEDIA_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}

DOWNLOAD_TITLES = {
    "social-research": "Анализ социальной значимости",
    "legal-acts": "Нормативные акты",
    "salary": "Расчет зарплаты",
    "support-letter": "Письмо поддержки",
    "presentation": "Презентация проекта",
    "scenario-plan": "Сценарный план",
}


@router.post("", response_model=ModuleRunCreateResponse)
def create_run(payload: ModuleRunCreateRequest, request: Request, response: Response):
    context = get_request_context(request, response)
    try:
        access = prepare_module_access(payload.module_slug, context)
    except ModuleAccessError as exc:
        raise HTTPException(status_code=402, detail={"message": str(exc)}) from exc
    try:
        run = create_module_run(payload.module_slug, payload.inputs, payload.presentation_variant)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    record_module_run_success(run, access, payload.inputs)
    return ModuleRunCreateResponse(
        run_id=run.run_id,
        status=run.status,
        module_slug=run.module_slug,
        title=run.title,
        message="Результат подготовлен. Можно скачать файл или сохранить работу.",
        downloads=run.downloads,
    )


@router.get("/{run_id}", response_model=ModuleRunResultResponse)
def run_status(run_id: str):
    return _result(run_id)


@router.get("/{run_id}/result", response_model=ModuleRunResultResponse)
def run_result(run_id: str):
    return _result(run_id)


@router.post("/{run_id}/improve", response_model=ModuleRunResultResponse)
def improve(run_id: str, payload: ImproveRequest):
    try:
        improve_run(run_id, payload.instruction)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"message": "Работа не найдена или срок хранения истек."}) from exc
    return _result(run_id)


@router.post("/{run_id}/email-file", response_model=EmailFileResponse)
def email_file(run_id: str, payload: EmailFileRequest):
    run = _load_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail={"message": "Работа не найдена или срок хранения истек."})
    try:
        saved = save_result_for_email(run, payload.email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    return EmailFileResponse(**saved)


@router.get("/{run_id}/download/{file_format}")
def download(run_id: str, file_format: str):
    run = _load_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail={"message": "Файл не найден или срок хранения истек."})
    if file_format not in run.files:
        raise HTTPException(status_code=404, detail={"message": "Такой формат для этой работы недоступен."})

    path = Path(run.files[file_format])
    if not path.exists():
        path = _regenerate_file(run, file_format)
    if not path.exists():
        raise HTTPException(status_code=404, detail={"message": "Файл временно недоступен. Запустите модуль еще раз."})

    filename = path.name if run.module_slug in {"support-letter", "salary"} and file_format == "docx" else f"{DOWNLOAD_TITLES.get(run.module_slug, run.module_slug)}.{file_format}"
    return FileResponse(path, media_type=MEDIA_TYPES.get(file_format, "application/octet-stream"), filename=filename)


def _result(run_id: str) -> ModuleRunResultResponse:
    run = _load_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail={"message": "Работа не найдена или срок хранения истек."})
    return ModuleRunResultResponse(
        run_id=run.run_id,
        status=run.status,
        module_slug=run.module_slug,
        title=run.title,
        summary=run.summary,
        sections=run.sections,
        downloads=run.downloads,
    )


def _load_run(run_id: str):
    return run_store.get(run_id) or load_persisted_run(run_id)


def _regenerate_file(run, file_format: str) -> Path:
    path = Path(settings.file_storage_dir) / run.run_id / f"{run.module_slug}.{file_format}"
    path.parent.mkdir(parents=True, exist_ok=True)
    if run.module_slug == "support-letter":
        return Path(run.files.get(file_format, path))
    if file_format == "docx":
        generate_docx(path, run.title, run.summary, run.sections)
    elif file_format == "pdf":
        generate_pdf(path, run.title, run.summary, run.sections)
    elif file_format == "pptx":
        generate_pptx(path, run.title, run.summary, run.sections, "grant_defense")
    else:
        return path
    run.files[file_format] = str(path)
    run_store.save(run)
    return path
