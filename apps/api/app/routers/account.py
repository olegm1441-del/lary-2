from fastapi import APIRouter, Request, Response

from app.schemas.modules import AccountWorksResponse, UsageResponse
from app.services.account_store import get_account_works, get_request_context, get_usage

router = APIRouter(prefix="/api", tags=["Account"])


@router.get("/usage", response_model=UsageResponse)
def usage(request: Request, response: Response):
    context = get_request_context(request, response)
    return UsageResponse(**get_usage(context))


@router.get("/account/works", response_model=AccountWorksResponse)
def account_works(request: Request, response: Response):
    context = get_request_context(request, response)
    return AccountWorksResponse(**get_account_works(context))
