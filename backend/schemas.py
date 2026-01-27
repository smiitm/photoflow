"""
schemas.py
Pydantic v2 request / response models for the PhotoFlow API.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# Project --------------------------------------------------

class ProjectCreate(BaseModel):
    """Body for POST /projects."""
    name: str = Field(..., min_length=1, max_length=255)


class ProjectUpdate(BaseModel):
    """Body for PATCH /projects/{id}.  All fields optional."""
    name: str | None = Field(default=None, min_length=1, max_length=255)


class ProjectResponse(BaseModel):
    """Returned by every project endpoint."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    created_at: datetime
    image_count: int = 0


# Image --------------------------------------------------

class ImageResponse(BaseModel):
    """Returned by the image upload endpoint."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    s3_key: str
