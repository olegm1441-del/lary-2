import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, Response

from app.schemas.modules import PaymentCreateRequest, PaymentCreateResponse, PaymentStatusResponse, PaymentWebhookRequest, PaymentWebhookResponse, PromoApplyRequest, PromoApplyResponse
from app.services.account_store import apply_promo_code, get_payment, get_request_context, handle_payment_webhook, package_config, record_payment_created

router = APIRouter(prefix="/api", tags=["Payments and promos"])
logger = logging.getLogger(__name__)


@router.post("/payments/create", response_model=PaymentCreateResponse)
def create_payment(payload: PaymentCreateRequest, request: Request, response: Response):
    context = get_request_context(request, response)
    package = package_config(payload.package)
    runs = package["runs"]
    amount = package["amount_rub"]
    payment_id = str(uuid4())
    try:
        record_payment_created(payment_id, payload.package, amount, runs, context)
    except Exception as exc:
        logger.warning("Payment placeholder persistence failed: %s", exc)
    return PaymentCreateResponse(
        payment_id=payment_id,
        status="created",
        amount_rub=amount,
        runs=runs,
        payment_url=f"/pay?payment_id={payment_id}&status=placeholder",
        message="Платежный слой подготовлен. Провайдера подключим перед приемом реальных оплат.",
    )


@router.get("/payments/{payment_id}", response_model=PaymentStatusResponse)
def payment_status(payment_id: str):
    payment = get_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail={"message": "Платеж не найден."})
    return PaymentStatusResponse(payment_id=payment_id, status=payment["status"], message="Статус платежа обновлен.")


@router.get("/payments/{payment_id}/status", response_model=PaymentStatusResponse)
def payment_status_legacy(payment_id: str):
    return payment_status(payment_id)


@router.post("/payments/webhook/{provider}", response_model=PaymentWebhookResponse)
def payment_webhook(provider: str, payload: PaymentWebhookRequest):
    try:
        result = handle_payment_webhook(provider, payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"message": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    return PaymentWebhookResponse(**result)


@router.post("/promos/apply", response_model=PromoApplyResponse)
def apply_promo(payload: PromoApplyRequest, request: Request, response: Response):
    context = get_request_context(request, response)
    try:
        result = apply_promo_code(payload.code, context)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"message": str(exc)}) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=410, detail={"message": str(exc)}) from exc
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail={"message": str(exc)}) from exc
    return PromoApplyResponse(**result)
