from fastapi import APIRouter
from core.config import settings

router = APIRouter()


@router.get("")
async def list_models():
    models = []

    if settings.ENABLE_WAN:
        t4_mode = settings.COLAB_T4_MODE
        models.append({
            "id": "wan",
            "name": "Wan 2.1 T4" if t4_mode else "Wan 2.6",
            "modes": ["t2v"] if t4_mode else ["t2v", "i2v"],
            "model_id": settings.WAN_MODEL_ID,
            "default_steps": settings.T4_WAN_STEPS if t4_mode else settings.WAN_DEFAULT_STEPS,
            "recommended_resolution": "512x320" if t4_mode else "832x480",
            "recommended_frames": settings.T4_WAN_FRAMES if t4_mode else 81,
            "vram_required_gb": 16 if t4_mode else 24,
            "description": "T4-friendly Wan 1.3B text-to-video profile." if t4_mode else "14B parameter model. Best quality T2V and I2V.",
        })

    if settings.ENABLE_COGVIDEO and not settings.COLAB_T4_MODE:
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
            "name": "FLUX.1-schnell",
            "modes": ["t2i"],
            "model_id": settings.FLUX_MODEL_ID,
            "default_steps": settings.FLUX_DEFAULT_STEPS,
            "recommended_resolution": "512x512" if settings.COLAB_T4_MODE else "1024x1024",
            "recommended_frames": None,
            "vram_required_gb": 16,
            "description": "Fast text-to-image. Use 512x512 on Colab T4.",
        })

    return models


@router.get("/domains")
async def list_domains():
    return [
        {"id": "general",    "enabled": settings.ENABLE_GENERAL,    "label": "General"},
        {"id": "cinematic",  "enabled": settings.ENABLE_CINEMATIC,   "label": "Cinematic"},
        {"id": "influencer", "enabled": settings.ENABLE_INFLUENCER,  "label": "Influencer"},
    ]
