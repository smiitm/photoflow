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

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy import func
from sqlalchemy.orm import Session

from deps import get_db
from models import Project, Image, Face
from schemas import ProjectCreate, ProjectUpdate, ProjectResponse, ImageResponse, SearchMatch, DownloadZipRequest
from celery_app import celery_app
from s3_utils import generate_presigned_url, upload_image, _s3_client, S3_BUCKET_NAME
from ai_utils import extract_faces
import tempfile
import os
import io
import zipfile
from fastapi.responses import StreamingResponse

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/heic",
    "image/heif",
}
MAX_ZIP_KEYS = 200  # Prevent accidentally streaming gigabytes into RAM


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


@router.post(
    "/{project_id}/upload",
    response_model=ImageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an image to a project",
)
def upload_project_image(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user),  # future auth
):
    """Upload a file to S3, create an Image record, and enqueue an AI processing task."""
    project = _get_project_or_404(project_id, db)
    # _check_ownership(project, current_user)  # future auth

    content_type = file.content_type or "image/jpeg"
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{content_type}'. Allowed: JPEG, PNG, WEBP, GIF, HEIC.",
        )

    file_bytes = file.file.read()
    
    s3_key = upload_image(
        source=file_bytes,
        project_id=str(project.id),
        content_type=content_type,
    )
    
    image = Image(project_id=project.id, s3_key=s3_key)
    db.add(image)
    db.commit()
    db.refresh(image)
    
    # Enqueue Celery task
    celery_app.send_task(
        "worker.process_image",
        kwargs={"image_id": str(image.id), "s3_key": s3_key}
    )
    
    return ImageResponse(id=image.id, project_id=image.project_id, s3_key=image.s3_key)


@router.post(
    "/{project_id}/search",
    response_model=list[SearchMatch],
    summary="Search for matching faces",
)
def search_project_faces(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user),  # future auth
):
    """Accept a selfie, extract vector, execute similarity search, and return presigned URLs."""
    project = _get_project_or_404(project_id, db)
    
    file_bytes = file.file.read()
    
    # Save selfie to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(file_bytes)
        tmp.flush()
        
    try:
        # Extract face from selfie
        result = extract_faces(tmp_path)
        faces = result.get("faces", [])
        
        if not faces:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No faces detected in the uploaded selfie."
            )
            
        # Use the first face found
        selfie_vector = faces[0]["embedding"]
        
        # Perform similarity search using pgvector l2_distance (<->)
        distance_expr = Face.embedding.l2_distance(selfie_vector)
        
        results = (
            db.query(Image.s3_key, distance_expr.label("distance"))
            .join(Face, Face.image_id == Image.id)
            .filter(Image.project_id == project.id)
            .filter(distance_expr < 0.55)  # Threshold for face recognition matches
            .order_by(distance_expr)
            .limit(20)
            .all()
        )
        
        matches = []
        seen_keys = set()
        
        for s3_key, dist in results:
            if s3_key not in seen_keys:
                seen_keys.add(s3_key)
                url = generate_presigned_url(s3_key)
                matches.append(SearchMatch(s3_key=s3_key, url=url, distance=dist))
                
        return matches
        
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post(
    "/{project_id}/download-zip",
    summary="Download multiple photos as a ZIP file",
)
def download_zip(
    project_id: uuid.UUID,
    body: DownloadZipRequest,
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user),  # future auth
):
    """Download the specified S3 keys and stream them as a ZIP archive."""
    project = _get_project_or_404(project_id, db)
    
    if not body.s3_keys:
        raise HTTPException(status_code=400, detail="No keys provided")

    if len(body.s3_keys) > MAX_ZIP_KEYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many keys requested. Maximum is {MAX_ZIP_KEYS}.",
        )

    # We will build the ZIP in memory
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for s3_key in body.s3_keys:
            # We must ensure the key belongs to the project for security
            if not s3_key.startswith(str(project.id) + "/"):
                continue
                
            try:
                # Fetch from S3
                response = _s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
                file_bytes = response["Body"].read()
                
                # Use just the filename for the zip entry
                filename = os.path.basename(s3_key)
                zip_file.writestr(filename, file_bytes)
            except Exception as e:
                # Log or ignore missing files
                print(f"Failed to fetch {s3_key}: {e}")
                
    # Seek to beginning
    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=photoflow-{project.id}.zip"}
    )
