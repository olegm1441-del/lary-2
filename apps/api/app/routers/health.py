from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.services.db import check_database

router = APIRouter()


@router.get("/")
def root():
    return {
        "status": "ok",
        "product": settings.app_name,
        "build_sha": settings.build_sha,
    }


@router.get("/health")
def health():
    return {
        "status": "ok",
        "build_sha": settings.build_sha,
    }


@router.get("/db/health")
def db_health():
    try:
        return check_database()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {e}")
