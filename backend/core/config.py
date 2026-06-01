from pydantic import field_validator
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "VideoAI"
    DEBUG: bool = False
    SECRET_KEY: str = "change-in-production"

    # Database (PostgreSQL)
    DATABASE_URL: str = "postgresql+asyncpg://videoai:videoai@localhost:5432/videoai"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://videoai:videoai@localhost:5432/videoai"

    # Redis + Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # Storage
    OUTPUT_DIR: str = "./outputs"
    MODEL_CACHE_DIR: str = "./model_cache"
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY: str = ""
    R2_SECRET_KEY: str = ""
    R2_BUCKET_NAME: str = "videoai"
    R2_PUBLIC_URL: str = ""

    # HuggingFace & Cloud APIs
    HF_TOKEN: str = ""
    REPLICATE_API_TOKEN: str = ""

    # GPU
    GPU_DEVICE: str = "cuda"
    GPU_COUNT: int = 1
    MAX_CONCURRENT_JOBS: int = 2
    JOB_TIMEOUT: int = 900
    COLAB_T4_MODE: bool = False

    # Models
    ENABLE_WAN: bool = True
    ENABLE_COGVIDEO: bool = True
    ENABLE_FLUX: bool = True
    ENABLE_LLM: bool = True

    LLM_MODEL_ID: str = "cognitivecomputations/dolphin-2.9-llama3-8b"
    WAN_MODEL_ID: str = "Wan-AI/Wan2.1-T2V-14B-Diffusers"
    WAN_I2V_MODEL_ID: str = "Wan-AI/Wan2.1-I2V-14B-480P-Diffusers"
    COGVIDEO_MODEL_ID: str = "THUDM/CogVideoX-5b"
    FLUX_MODEL_ID: str = "black-forest-labs/FLUX.1-schnell"

    # Default generation params
    WAN_DEFAULT_STEPS: int = 50
    COGVIDEO_DEFAULT_STEPS: int = 50
    FLUX_DEFAULT_STEPS: int = 4

    # Conservative defaults for Colab T4 / 16GB VRAM.
    T4_WAN_STEPS: int = 12
    T4_WAN_WIDTH: int = 512
    T4_WAN_HEIGHT: int = 320
    T4_WAN_FRAMES: int = 33
    T4_WAN_FPS: int = 8
    T4_FLUX_WIDTH: int = 512
    T4_FLUX_HEIGHT: int = 512

    # Content domains enabled
    ENABLE_GENERAL: bool = True
    ENABLE_CINEMATIC: bool = True
    ENABLE_INFLUENCER: bool = True

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    @field_validator("HF_TOKEN", "REPLICATE_API_TOKEN", mode="before")
    @classmethod
    def empty_placeholder_tokens(cls, value):
        if not isinstance(value, str):
            return value
        if value.strip().lower() in {"hf_your_token_here", "your_replicate_api_token_here"}:
            return ""
        return value


    class Config:
        env_file = ".env"


settings = Settings()
