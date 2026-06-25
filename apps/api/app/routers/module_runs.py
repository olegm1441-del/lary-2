from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.schemas.modules import ImproveRequest, ModuleRunCreateRequest, ModuleRunCreateResponse, ModuleRunResultResponse
from app.services.module_engine import create_module_run, improve_run
from app.services.run_store import run_store

router = APIRouter(prefix="/api/module-runs", tags=["Module runs"])

MEDIA_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


@router.post("", response_model=ModuleRunCreateResponse)
def create_run(payload: ModuleRunCreateRequest):
    try:
        run = create_module_run(payload.module_slug, payload.inputs, payload.presentation_variant)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
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


@router.get("/{run_id}/download/{file_format}")
def download(run_id: str, file_format: str):
    run = run_store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail={"message": "Файл не найден или срок хранения истек."})
    if file_format not in run.files:
        raise HTTPException(status_code=404, detail={"message": "Такой формат для этой работы недоступен."})

    path = Path(run.files[file_format])
    if not path.exists():
        raise HTTPException(status_code=404, detail={"message": "Файл временно недоступен. Запустите модуль еще раз."})

    return FileResponse(path, media_type=MEDIA_TYPES.get(file_format, "application/octet-stream"), filename=path.name)


def _result(run_id: str) -> ModuleRunResultResponse:
    run = run_store.get(run_id)
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
