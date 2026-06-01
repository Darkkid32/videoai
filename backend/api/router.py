from fastapi import APIRouter
from api.routes import generate, jobs, characters, assets, models_info, chat

api_router = APIRouter()
api_router.include_router(generate.router,    prefix="/generate",    tags=["Generation"])
api_router.include_router(jobs.router,        prefix="/jobs",        tags=["Jobs"])
api_router.include_router(characters.router,  prefix="/characters",  tags=["Characters"])
api_router.include_router(assets.router,      prefix="/assets",      tags=["Assets"])
api_router.include_router(models_info.router, prefix="/models",      tags=["Models"])
api_router.include_router(chat.router,        prefix="/chat",        tags=["Chat"])
