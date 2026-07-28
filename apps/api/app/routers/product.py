from fastapi import APIRouter

from app.services.product_registry import get_product_registry

router = APIRouter(prefix="/api", tags=["Product"])


@router.get("/contests")
def list_contests():
    registry = get_product_registry()
    return {"items": [item.model_dump() for item in registry.get_contests() if item.status != "hidden"]}

