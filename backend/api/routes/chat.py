from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict
import logging

from pipelines.llm import LLMPipeline

router = APIRouter()
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    temperature: float = 0.7
    max_tokens: int = 1024

class ChatResponse(BaseModel):
    response: str

@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    logger.info(f"Received chat request with {len(req.messages)} messages")
    
    # Check if pipeline exists or can be loaded
    pipeline = LLMPipeline.load()
    if not pipeline:
        raise HTTPException(status_code=503, detail="LLM Pipeline not available or disabled")
        
    try:
        response_text = pipeline.generate_chat(
            messages=req.messages,
            max_new_tokens=req.max_tokens,
            temperature=req.temperature
        )
        return ChatResponse(response=response_text)
    except Exception as e:
        logger.error(f"Chat generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/unload")
async def unload_model():
    """Unload LLM to free VRAM before generating a video"""
    pipeline = LLMPipeline.load()
    if pipeline:
        pipeline.unload()
    return {"status": "success", "message": "LLM unloaded"}
