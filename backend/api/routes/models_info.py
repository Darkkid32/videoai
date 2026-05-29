from fastapi import APIRouter
from core.config import settings

router = APIRouter()


@router.get("")
async def list_models():
    models = []

    if settings.ENABLE_WAN:
        models.append({
            "id": "wan",
            "name": "Wan 2.6",
            "modes": ["t2v", "i2v"],
            "model_id": settings.WAN_MODEL_ID,
            "default_steps": settings.WAN_DEFAULT_STEPS,
            "recommended_resolution": "832x480",
            "recommended_frames": 81,
            "vram_required_gb": 24,
            "description": "14B parameter model. Best quality T2V and I2V.",
        })

    if settings.ENABLE_COGVIDEO:
        models.append({
            "id": "cogvideo",
            "name": "CogVideoX",
            "modes": ["t2v"],
            "model_id": settings.COGVIDEO_MODEL_ID,
            "default_steps": settings.COGVIDEO_DEFAULT_STEPS,
            "recommended_resolution": "720x480",
            "recommended_frames": 49,
            "vram_required_gb": 16,
            "description": "5B parameter model. Fast coherent T2V.",
        })

    if settings.ENABLE_FLUX:
        models.append({
            "id": "flux",
            "name": "FLUX.1-dev",
            "modes": ["t2i"],
            "model_id": settings.FLUX_MODEL_ID,
            "default_steps": settings.FLUX_DEFAULT_STEPS,
            "recommended_resolution": "1024x1024",
            "recommended_frames": None,
            "vram_required_gb": 16,
            "description": "Premium text-to-image. Best for keyframe and reference generation.",
        })

    return models


@router.get("/domains")
async def list_domains():
    return [
        {"id": "general",    "enabled": settings.ENABLE_GENERAL,    "label": "General"},
        {"id": "cinematic",  "enabled": settings.ENABLE_CINEMATIC,   "label": "Cinematic"},
        {"id": "influencer", "enabled": settings.ENABLE_INFLUENCER,  "label": "Influencer"},
    ]
