from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import Optional, List
from core.database import get_db
from db.models import Job, JobStatus

router = APIRouter()


@router.get("")
async def list_jobs(
    limit: int = Query(30, le=100),
    offset: int = 0,
    engine: Optional[str] = None,
    status: Optional[str] = None,
    content_domain: Optional[str] = None,
    project_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(Job).order_by(desc(Job.created_at)).limit(limit).offset(offset)
    if engine:
        q = q.where(Job.engine == engine)
    if status:
        q = q.where(Job.status == status)
    if content_domain:
        q = q.where(Job.content_domain == content_domain)
    if project_id:
        q = q.where(Job.project_id == project_id)
    result = await db.execute(q)
    jobs = result.scalars().all()
    return [_out(j) for j in jobs]


@router.get("/stats")
async def stats(db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count(Job.id)))).scalar()
    done = (await db.execute(select(func.count(Job.id)).where(Job.status == JobStatus.done))).scalar()
    running = (await db.execute(select(func.count(Job.id)).where(Job.status == JobStatus.running))).scalar()
    queued = (await db.execute(select(func.count(Job.id)).where(Job.status == JobStatus.queued))).scalar()
    failed = (await db.execute(select(func.count(Job.id)).where(Job.status == JobStatus.failed))).scalar()
    avg_time = (await db.execute(
        select(func.avg(Job.inference_time_seconds)).where(Job.status == JobStatus.done)
    )).scalar()
    return {
        "total": total, "done": done, "running": running,
        "queued": queued, "failed": failed,
        "avg_inference_seconds": round(avg_time or 0, 1),
    }


@router.get("/{job_id}")
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    job = await _get_or_404(job_id, db)
    return _out(job)


@router.delete("/{job_id}")
async def cancel_job(job_id: str, db: AsyncSession = Depends(get_db)):
    job = await _get_or_404(job_id, db)
    if job.celery_task_id and job.status in (JobStatus.queued, JobStatus.running):
        from workers.celery_app import celery_app
        celery_app.control.revoke(job.celery_task_id, terminate=True, signal="SIGKILL")
    job.status = JobStatus.cancelled
    await db.commit()
    return {"message": "Cancelled."}


async def _get_or_404(job_id: str, db: AsyncSession) -> Job:
    r = await db.execute(select(Job).where(Job.id == job_id))
    job = r.scalar_one_or_none()
    if not job:
        raise HTTPException(404, f"Job {job_id} not found.")
    return job


def _out(j: Job) -> dict:
    return {
        "id": j.id,
        "engine": j.engine,
        "mode": j.mode,
        "content_domain": j.content_domain.value if j.content_domain else "general",
        "prompt": j.prompt,
        "optimized_prompt": j.optimized_prompt,
        "status": j.status.value if j.status else "queued",
        "progress": j.progress,
        "output_url": j.output_url,
        "error": j.error,
        "inference_time_seconds": j.inference_time_seconds,
        "lora_path": j.lora_path,
        "created_at": str(j.created_at),
    }
