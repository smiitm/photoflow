import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from database import Base

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    images = relationship("Image", back_populates="project", cascade="all, delete-orphan", passive_deletes=True)

class Image(Base):
    __tablename__ = "images"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    s3_key = Column(String, nullable=False)
    
    project = relationship("Project", back_populates="images")
    faces = relationship("Face", back_populates="image", cascade="all, delete-orphan", passive_deletes=True)

class Face(Base):
    __tablename__ = "faces"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    image_id = Column(UUID(as_uuid=True), ForeignKey("images.id", ondelete="CASCADE"))
    embedding = Column(Vector(128))  # The 128-d AI face array
    bounding_box = Column(JSON)
    
    image = relationship("Image", back_populates="faces")