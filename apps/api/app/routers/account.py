from fastapi import APIRouter, HTTPException, Request, Response

from app.schemas.modules import AccountWorksResponse, DeleteWorkResponse, UsageResponse
from app.services.account_store import delete_work, get_account_works, get_request_context, get_usage

router = APIRouter(prefix="/api", tags=["Account"])


@router.get("/usage", response_model=UsageResponse)
def usage(request: Request, response: Response):
    context = get_request_context(request, response)
    return UsageResponse(**get_usage(context))


@router.get("/account/works", response_model=AccountWorksResponse)
def account_works(request: Request, response: Response):
    context = get_request_context(request, response)
    return AccountWorksResponse(**get_account_works(context))


@router.delete("/account/works/{run_id}", response_model=DeleteWorkResponse)
def remove_work(run_id: str, request: Request, response: Response):
    context = get_request_context(request, response)
    try:
        result = delete_work(run_id, context)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"message": str(exc)}) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail={"message": str(exc)}) from exc
    return DeleteWorkResponse(**result)
