from fastapi import APIRouter, HTTPException, Request, Response

from app.schemas.modules import (
    ProjectAttachRequest,
    ProjectAttachResponse,
    ProjectCreateRequest,
    ProjectCreateResponse,
    ProjectUpdateRequest,
    ProjectsResponse,
)
from app.services.account_store import (
    attach_work_to_project,
    create_project,
    get_projects,
    get_request_context,
    update_project_contest,
)

router = APIRouter(prefix="/api/projects", tags=["Projects"])


@router.get("", response_model=ProjectsResponse)
def list_projects(request: Request, response: Response):
    context = get_request_context(request, response)
    return ProjectsResponse(**get_projects(context))


@router.post("", response_model=ProjectCreateResponse)
def create(payload: ProjectCreateRequest, request: Request, response: Response):
    context = get_request_context(request, response)
    try:
        result = create_project(payload.title, payload.competition, context, contest_slug=payload.contest_slug)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    return ProjectCreateResponse(**result)


@router.patch("/{project_id}", response_model=ProjectCreateResponse)
def update(project_id: str, payload: ProjectUpdateRequest, request: Request, response: Response):
    context = get_request_context(request, response)
    try:
        result = update_project_contest(project_id, payload.contest_slug, context)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"message": str(exc)}) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail={"message": str(exc)}) from exc
    return ProjectCreateResponse(**result)


@router.post("/{project_id}/attach", response_model=ProjectAttachResponse)
def attach(project_id: str, payload: ProjectAttachRequest, request: Request, response: Response):
    context = get_request_context(request, response)
    try:
        result = attach_work_to_project(project_id, payload.run_id, context)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"message": str(exc)}) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail={"message": str(exc)}) from exc
    return ProjectAttachResponse(**result)
