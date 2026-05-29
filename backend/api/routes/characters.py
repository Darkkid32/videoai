from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
import uuid, shutil, os

from core.database import get_db
from core.config import settings
from db.models import Character

router = APIRouter()


class CharacterCreate(BaseModel):
    name: str
    description: str
    style_tags: Optional[List[str]] = None
    project_id: Optional[str] = None


class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    style_tags: Optional[List[str]] = None
    lora_path: Optional[str] = None


@router.get("")
async def list_characters(
    project_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    q = select(Character).order_by(Character.created_at.desc())
    if project_id:
        q = q.where(Character.project_id == project_id)
    result = await db.execute(q)
    return [_out(c) for c in result.scalars().all()]


@router.post("")
async def create_character(data: CharacterCreate, db: AsyncSession = Depends(get_db)):
    char = Character(
        name=data.name,
        description=data.description,
        style_tags=data.style_tags or [],
        project_id=data.project_id,
    )
    db.add(char)
    await db.commit()
    await db.refresh(char)
    return _out(char)


@router.get("/{char_id}")
async def get_character(char_id: str, db: AsyncSession = Depends(get_db)):
    char = await _get_or_404(char_id, db)
    return _out(char)


@router.patch("/{char_id}")
async def update_character(char_id: str, data: CharacterUpdate, db: AsyncSession = Depends(get_db)):
    char = await _get_or_404(char_id, db)
    if data.name is not None:
        char.name = data.name
    if data.description is not None:
        char.description = data.description
    if data.style_tags is not None:
        char.style_tags = data.style_tags
    if data.lora_path is not None:
        char.lora_path = data.lora_path
    await db.commit()
    await db.refresh(char)
    return _out(char)


@router.delete("/{char_id}")
async def delete_character(char_id: str, db: AsyncSession = Depends(get_db)):
    char = await _get_or_404(char_id, db)
    await db.delete(char)
    await db.commit()
    return {"message": "Deleted."}


@router.post("/{char_id}/reference-image")
async def upload_reference_image(
    char_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    char = await _get_or_404(char_id, db)
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "webp"):
        raise HTTPException(400, "Unsupported format.")
    fname = f"char_{char_id}_{uuid.uuid4().hex[:8]}.{ext}"
    dest = os.path.join(settings.OUTPUT_DIR, "uploads", fname)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    char.reference_image_url = f"/outputs/uploads/{fname}"
    await db.commit()
    await db.refresh(char)
    return _out(char)


async def _get_or_404(char_id: str, db: AsyncSession) -> Character:
    r = await db.execute(select(Character).where(Character.id == char_id))
    c = r.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Character not found.")
    return c


def _out(c: Character) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "description": c.description,
        "reference_image_url": c.reference_image_url,
        "lora_path": c.lora_path,
        "style_tags": c.style_tags or [],
        "project_id": c.project_id,
        "created_at": str(c.created_at),
    }
