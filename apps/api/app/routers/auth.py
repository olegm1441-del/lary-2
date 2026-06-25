from fastapi import APIRouter, HTTPException, Request, Response

from app.schemas.modules import MagicLinkConsumeRequest, MagicLinkConsumeResponse, MagicLinkRequest, MagicLinkRequestResponse
from app.services.account_store import consume_magic_link, get_request_context, request_magic_link

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/magic-link/request", response_model=MagicLinkRequestResponse)
def magic_link_request(payload: MagicLinkRequest, request: Request, response: Response):
    context = get_request_context(request, response)
    try:
        result = request_magic_link(payload.email, context)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    return MagicLinkRequestResponse(**result)


@router.post("/magic-link/consume", response_model=MagicLinkConsumeResponse)
def magic_link_consume(payload: MagicLinkConsumeRequest, response: Response):
    try:
        result = consume_magic_link(payload.token, response)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    return MagicLinkConsumeResponse(**result)
