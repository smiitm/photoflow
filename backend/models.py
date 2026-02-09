import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from database import Base

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    images = relationship("Image", back_populates="project", cascade="all, delete-orphan", passive_deletes=True)

class Image(Base):
    __tablename__ = "images"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    s3_key = Column(String, nullable=False)
    
    project = relationship("Project", back_populates="images")
    faces = relationship("Face", back_populates="image", cascade="all, delete-orphan", passive_deletes=True)

class Face(Base):
    __tablename__ = "faces"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    image_id = Column(UUID(as_uuid=True), ForeignKey("images.id", ondelete="CASCADE"), nullable=False, index=True)
    embedding = Column(Vector(128))  # The 128-d AI face array
    bounding_box = Column(JSON)
    
    image = relationship("Image", back_populates="faces")