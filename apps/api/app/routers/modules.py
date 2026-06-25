from fastapi import APIRouter, HTTPException

from app.data.modules import get_module, get_modules
from app.schemas.modules import ModuleItem, ModulesResponse

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
