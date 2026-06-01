from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import Optional, Literal
import uuid, shutil, os

from core.database import get_db
from core.config import settings
from db.models import Job, Character, ContentDomain, JobStatus
from workers.tasks import run_generation
from intelligence.prompt_optimizer import PromptOptimizer

router = APIRouter()
optimizer = PromptOptimizer()


# ── Schemas ───────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    engine: Literal["wan", "cogvideo", "flux"] = "wan"
    mode: Literal["t2v", "i2v", "t2i"] = "t2v"
    content_domain: Literal["general", "cinematic", "influencer"] = "general"
    prompt: str = Field(..., min_length=3, max_length=4000)
    negative_prompt: Optional[str] = None
    style_prompt: Optional[str] = None
    input_image_url: Optional[str] = None
    character_id: Optional[str] = None
    project_id: Optional[str] = None
    lora_path: Optional[str] = None
    optimize_prompt: bool = True
    # Generation params
    steps: Optional[int] = None
    cfg_scale: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    num_frames: Optional[int] = None
    fps: Optional[int] = None
    seed: Optional[int] = None
    priority: int = Field(default=5, ge=1, le=10)


class JobOut(BaseModel):
    id: str
    engine: str
    mode: str
    content_domain: str
    prompt: str
    optimized_prompt: Optional[str]
    status: str
    progress: int
    output_url: Optional[str]
    error: Optional[str]
    inference_time_seconds: Optional[float]
    created_at: str

    class Config:
        from_attributes = True


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("", response_model=JobOut)
async def generate(req: GenerateRequest, db: AsyncSession = Depends(get_db)):
    # Validate engine
    if req.engine == "wan" and not settings.ENABLE_WAN:
        raise HTTPException(400, "Wan engine disabled.")
    if req.engine == "cogvideo" and (not settings.ENABLE_COGVIDEO or settings.COLAB_T4_MODE):
        raise HTTPException(400, "CogVideoX engine disabled for this profile.")
    if req.engine == "flux" and not settings.ENABLE_FLUX:
        raise HTTPException(400, "FLUX engine disabled.")
    if req.mode == "i2v":
        if not req.input_image_url:
            raise HTTPException(400, "input_image_url required for i2v mode.")
        if req.engine == "wan" and settings.COLAB_T4_MODE:
            raise HTTPException(400, "Image-to-video is not available in T4/Colab mode.")

    # Validate content domain
    domain_map = {
        "general": settings.ENABLE_GENERAL,
        "cinematic": settings.ENABLE_CINEMATIC,
        "influencer": settings.ENABLE_INFLUENCER,
    }
    if not domain_map.get(req.content_domain, False):
        raise HTTPException(400, f"Content domain '{req.content_domain}' is disabled.")

    # Fetch character if provided
    character = None
    if req.character_id:
        result = await db.execute(select(Character).where(Character.id == req.character_id))
        character = result.scalar_one_or_none()
        if not character:
            raise HTTPException(404, "Character not found.")

    # Optimize prompt
    optimized = None
    final_prompt = req.prompt
    if req.optimize_prompt:
        optimized = optimizer.optimize(
            prompt=req.prompt,
            domain=req.content_domain,
            engine=req.engine,
            character=character,
            style_prompt=req.style_prompt,
        )
        final_prompt = optimized

    # Build params
    params = {k: v for k, v in {
        "steps": req.steps,
        "cfg_scale": req.cfg_scale,
        "width": req.width,
        "height": req.height,
        "num_frames": req.num_frames,
        "fps": req.fps,
        "seed": req.seed,
    }.items() if v is not None}

    job = Job(
        engine=req.engine,
        mode=req.mode,
        content_domain=ContentDomain(req.content_domain),
        prompt=req.prompt,
        optimized_prompt=optimized,
        negative_prompt=req.negative_prompt,
        style_prompt=req.style_prompt,
        input_image_url=req.input_image_url,
        character_id=req.character_id,
        project_id=req.project_id,
        lora_path=req.lora_path or (character.lora_path if character else None),
        params=params,
        priority=req.priority,
        status=JobStatus.queued,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Dispatch to Celery
    task = run_generation.apply_async(
        args=[job.id],
        priority=10 - req.priority,  # Celery: lower number = higher priority
    )
    job.celery_task_id = task.id
    await db.commit()
    await db.refresh(job)

    return _out(job)


@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "webp"):
        raise HTTPException(400, "Unsupported format. Use jpg/png/webp.")
    fname = f"{uuid.uuid4().hex}.{ext}"
    dest = os.path.join(settings.OUTPUT_DIR, "uploads", fname)
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"url": f"/outputs/uploads/{fname}"}


def _out(job: Job) -> dict:
    return {
        "id": job.id,
        "engine": job.engine,
        "mode": job.mode,
        "content_domain": job.content_domain.value if job.content_domain else "general",
        "prompt": job.prompt,
        "optimized_prompt": job.optimized_prompt,
        "status": job.status.value if job.status else "queued",
        "progress": job.progress,
        "output_url": job.output_url,
        "error": job.error,
        "inference_time_seconds": job.inference_time_seconds,
        "created_at": str(job.created_at),
    }
