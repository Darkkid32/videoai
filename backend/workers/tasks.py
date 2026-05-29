"""
Celery generation tasks.
Uses synchronous SQLAlchemy for Celery (no event loop conflicts).
"""
import time, os, logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from workers.celery_app import celery_app
from core.config import settings

logger = logging.getLogger(__name__)


def _get_session():
    engine = create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    return Session()


def _update(session, job_id: str, **kwargs):
    from db.models import Job
    job = session.query(Job).filter(Job.id == job_id).first()
    if job:
        for k, v in kwargs.items():
            setattr(job, k, v)
        session.commit()
    return job


@celery_app.task(bind=True, name="run_generation")
def run_generation(self, job_id: str):
    db = _get_session()
    job = _update(db, job_id, status="running", progress=5)

    if not job:
        logger.error(f"Job {job_id} not found in DB.")
        return

    logger.info(f"[{job_id}] Starting | engine={job.engine} mode={job.mode} domain={job.content_domain}")
    start = time.time()

    try:
        params = job.params or {}

        if job.engine == "wan":
            output_path = _run_wan(db, job, params)
        elif job.engine == "cogvideo":
            output_path = _run_cogvideo(db, job, params)
        elif job.engine == "flux":
            output_path = _run_flux(db, job, params)
        else:
            raise ValueError(f"Unknown engine: {job.engine}")

        elapsed = round(time.time() - start, 2)
        output_url = f"/outputs/{os.path.basename(output_path)}"

        # Save asset record
        _save_asset(db, job.id, output_path, output_url)

        _update(db, job_id,
                status="done",
                progress=100,
                output_url=output_url,
                inference_time_seconds=elapsed)

        logger.info(f"[{job_id}] Done in {elapsed}s → {output_url}")

    except Exception as e:
        logger.exception(f"[{job_id}] Failed: {e}")
        _update(db, job_id, status="failed", error=str(e)[:2000])
    finally:
        db.close()


# ── Pipeline runners ──────────────────────────────────────────────────────────

def _download_url(url: str, ext: str) -> str:
    import os, requests, uuid
    out_dir = settings.OUTPUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{uuid.uuid4()}.{ext}")
    r = requests.get(url, timeout=60)
    with open(out_path, "wb") as f:
        f.write(r.content)
    return out_path

def _run_wan(db, job, params: dict) -> str:
    from pipelines.wan import WanPipeline
    _update(db, job.id, progress=20)
    def progress_cb(prog): _update(db, job.id, progress=20 + int(prog * 0.7))
    pipe = WanPipeline.load()
    return pipe.generate(
        prompt=job.optimized_prompt or job.prompt,
        negative_prompt=params.get("negative_prompt"),
        mode=job.mode,
        input_image_url=params.get("input_image_url"),
        lora_path=job.lora_path,
        steps=params.get("steps", settings.WAN_DEFAULT_STEPS),
        progress_cb=progress_cb
    )

def _run_cogvideo(db, job, params: dict) -> str:
    from pipelines.cogvideo import CogVideoPipeline
    _update(db, job.id, progress=20)
    def progress_cb(prog): _update(db, job.id, progress=20 + int(prog * 0.7))
    pipe = CogVideoPipeline.load()
    return pipe.generate(
        prompt=job.optimized_prompt or job.prompt,
        negative_prompt=params.get("negative_prompt"),
        lora_path=job.lora_path,
        steps=params.get("steps", settings.COGVIDEO_DEFAULT_STEPS),
        progress_cb=progress_cb
    )

def _run_flux(db, job, params: dict) -> str:
    from pipelines.flux import FluxPipeline
    _update(db, job.id, progress=20)
    def progress_cb(prog): _update(db, job.id, progress=20 + int(prog * 0.7))
    pipe = FluxPipeline.load()
    return pipe.generate(
        prompt=job.optimized_prompt or job.prompt,
        lora_path=job.lora_path,
        steps=params.get("steps", settings.FLUX_DEFAULT_STEPS),
        progress_cb=progress_cb
    )


def _save_asset(db, job_id: str, file_path: str, url: str):
    from db.models import Asset
    import os
    ext = file_path.rsplit(".", 1)[-1].lower()
    asset_type = "video" if ext == "mp4" else "image"
    size = os.path.getsize(file_path) if os.path.exists(file_path) else None
    asset = Asset(
        job_id=job_id,
        asset_type=asset_type,
        file_path=file_path,
        url=url,
        file_size_bytes=size,
    )
    db.add(asset)
    db.commit()
