"""
routers/projects.py
CRUD endpoints for project (event) management.

Auth readiness
--------------
Every endpoint receives its dependencies through FastAPI's DI system.
When authentication is added, inject a ``current_user`` dependency and:

  1. On CREATE  → set ``project.owner_id = current_user.id``
  2. On LIST    → filter ``Project.owner_id == current_user.id``
  3. On GET     → verify ownership or raise 403
  4. On UPDATE  → verify ownership or raise 403
  5. On DELETE  → verify ownership or raise 403

No structural changes to this file will be needed — just add the
dependency parameter and the ownership filter/check.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from deps import get_db
from models import Project, Image
from schemas import ProjectCreate, ProjectUpdate, ProjectResponse


router = APIRouter(prefix="/projects", tags=["Projects"])


# Helpers --------------------------------------------------

def _project_to_response(project: Project, image_count: int) -> ProjectResponse:
    """Convert an ORM model + count into a Pydantic response."""
    return ProjectResponse(
        id=project.id,
        name=project.name,
        created_at=project.created_at,
        image_count=image_count,
    )


def _get_project_or_404(
    project_id: uuid.UUID,
    db: Session,
) -> Project:
    """Fetch a project by ID or raise 404."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    return project


# Endpoints --------------------------------------------------

@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
)
def create_project(
    body: ProjectCreate,
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user),  # future auth
):
    """Create a new project (event) that photos can be uploaded into."""
    project = Project(name=body.name)
    # project.owner_id = current_user.id  # future auth
    db.add(project)
    db.commit()
    db.refresh(project)
    return _project_to_response(project, image_count=0)


@router.get(
    "",
    response_model=list[ProjectResponse],
    summary="List all projects",
)
def list_projects(
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user),  # future auth
):
    """Return every project, newest first, with image counts."""
    # Single query with a LEFT JOIN count to avoid N+1
    results = (
        db.query(Project, func.count(Image.id).label("image_count"))
        .outerjoin(Image, Image.project_id == Project.id)
        .group_by(Project.id)
        .order_by(Project.created_at.desc())
        # .filter(Project.owner_id == current_user.id)  # future auth
        .all()
    )
    return [_project_to_response(proj, cnt) for proj, cnt in results]


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get a single project",
)
def get_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user),  # future auth
):
    """Retrieve a project by its UUID."""
    project = _get_project_or_404(project_id, db)
    # _check_ownership(project, current_user)  # ← future auth
    image_count = db.query(func.count(Image.id)).filter(Image.project_id == project.id).scalar()
    return _project_to_response(project, image_count)


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update a project",
)
def update_project(
    project_id: uuid.UUID,
    body: ProjectUpdate,
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user),  # future auth
):
    """Update mutable fields on a project (currently just the name)."""
    project = _get_project_or_404(project_id, db)
    # _check_ownership(project, current_user)  # ← future auth

    if body.name is not None:
        project.name = body.name

    db.commit()
    db.refresh(project)
    image_count = db.query(func.count(Image.id)).filter(Image.project_id == project.id).scalar()
    return _project_to_response(project, image_count)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project",
)
def delete_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user),  # future auth
):
    """Delete a project and cascade-remove all its images and faces."""
    project = _get_project_or_404(project_id, db)
    # _check_ownership(project, current_user)  # future auth
    db.delete(project)
    db.commit()
    return None
