from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime,
    JSON, ForeignKey, Boolean, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base
import uuid, enum


def gen_id():
    return str(uuid.uuid4())


class ContentDomain(str, enum.Enum):
    general = "general"
    cinematic = "cinematic"
    influencer = "influencer"


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"
    cancelled = "cancelled"


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    style_preset = Column(JSON, nullable=True)  # default style config
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    jobs = relationship("Job", back_populates="project")
    characters = relationship("Character", back_populates="project")


class Character(Base):
    """Character memory — stores embedding + visual reference for consistency."""
    __tablename__ = "characters"

    id = Column(String, primary_key=True, default=gen_id)
    project_id = Column(String, ForeignKey("projects.id"), nullable=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)       # text description
    reference_image_url = Column(String, nullable=True)
    lora_path = Column(String, nullable=True)        # trained LoRA for this character
    style_tags = Column(JSON, nullable=True)         # ["cinematic", "realistic", ...]
    embedding_cache = Column(JSON, nullable=True)    # cached prompt embeddings
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project", back_populates="characters")
    jobs = relationship("Job", back_populates="character")


class Asset(Base):
    """Generated asset — video, image, or audio output."""
    __tablename__ = "assets"

    id = Column(String, primary_key=True, default=gen_id)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=True)
    asset_type = Column(String, nullable=False)      # video | image | audio
    file_path = Column(String, nullable=False)
    url = Column(String, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    fps = Column(Integer, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    asset_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    job = relationship("Job", back_populates="assets")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=gen_id)
    celery_task_id = Column(String, nullable=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=True)
    character_id = Column(String, ForeignKey("characters.id"), nullable=True)

    # Generation config
    engine = Column(String, nullable=False)           # wan | cogvideo | flux
    mode = Column(String, nullable=False)             # t2v | i2v | t2i
    content_domain = Column(
        SAEnum(ContentDomain), default=ContentDomain.general, nullable=False
    )

    # Prompts
    prompt = Column(Text, nullable=False)
    optimized_prompt = Column(Text, nullable=True)    # after prompt optimizer
    negative_prompt = Column(Text, nullable=True)
    style_prompt = Column(Text, nullable=True)        # appended style tokens

    # Params
    params = Column(JSON, nullable=True)
    input_image_url = Column(String, nullable=True)
    lora_path = Column(String, nullable=True)

    # State
    status = Column(SAEnum(JobStatus), default=JobStatus.queued, nullable=False, index=True)
    progress = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    priority = Column(Integer, default=5)             # 1=highest, 10=lowest

    # Output
    output_url = Column(String, nullable=True)
    inference_time_seconds = Column(Float, nullable=True)

    # Meta
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project", back_populates="jobs")
    character = relationship("Character", back_populates="jobs")
    assets = relationship("Asset", back_populates="job")
