import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.schemas.modules import PaymentCreateRequest, PaymentCreateResponse, PaymentStatusResponse, PromoApplyRequest, PromoApplyResponse
from app.services.account_store import record_payment_created

router = APIRouter(prefix="/api", tags=["Payments and promos"])
logger = logging.getLogger(__name__)


@router.post("/payments/create", response_model=PaymentCreateResponse)
def create_payment(payload: PaymentCreateRequest):
    runs = 1 if payload.package == "single" else 6
    amount = 320 if payload.package == "single" else 320 * 6
    payment_id = str(uuid4())
    try:
        record_payment_created(payment_id, payload.package, amount, runs)
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


@router.get("/payments/{payment_id}/status", response_model=PaymentStatusResponse)
def payment_status(payment_id: str):
    return PaymentStatusResponse(payment_id=payment_id, status="placeholder", message="Платеж ожидает подключения провайдера.")


@router.post("/promos/apply", response_model=PromoApplyResponse)
def apply_promo(payload: PromoApplyRequest):
    code = payload.code.strip().upper()
    if code != "LARY-START":
        raise HTTPException(status_code=404, detail={"message": "Такой промокод не найден."})
    return PromoApplyResponse(status="applied", added_runs=3, remaining_runs=3, message="Промокод применен. Добавлено запусков: 3.")
