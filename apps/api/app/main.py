import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import account, ai, auth, field_assistant, health, module_runs, modules, payments, product, projects, speech
from app.services.account_store import ensure_account_schema
from app.services.product_registry import get_product_registry
from app.services.vosk_model_manager import ensure_vosk_model_available

logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(account.router)
app.include_router(auth.router)
app.include_router(ai.router)
app.include_router(field_assistant.router)
app.include_router(product.router)
app.include_router(modules.router)
app.include_router(module_runs.router)
app.include_router(payments.router)
app.include_router(projects.router)
app.include_router(speech.router)


@app.on_event("startup")
def prepare_runtime_dependencies() -> None:
    if settings.product_registry_runtime_enabled:
        get_product_registry()
    ensure_vosk_model_available()
    try:
        ensure_account_schema()
    except Exception as exc:
        logger.warning("Account schema initialization failed: %s", exc)
