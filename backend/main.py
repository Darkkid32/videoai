from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging, os

from api.router import api_router
from core.config import settings
from core.database import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("VideoAI starting up...")
    await init_db()
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.join(settings.OUTPUT_DIR, "uploads"), exist_ok=True)
    os.makedirs(settings.MODEL_CACHE_DIR, exist_ok=True)
    yield
    logger.info("VideoAI shut down.")


app = FastAPI(
    title="VideoAI",
    description="Frontier-level internal AI video generation platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
app.mount("/outputs", StaticFiles(directory=settings.OUTPUT_DIR), name="outputs")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0", "gpu": settings.GPU_DEVICE}

from fastapi.responses import RedirectResponse
@app.get("/")
async def root():
    return RedirectResponse(url="/docs")
