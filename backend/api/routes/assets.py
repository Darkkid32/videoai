from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional
from core.database import get_db
from db.models import Asset

router = APIRouter()


@router.get("")
async def list_assets(
    limit: int = Query(50, le=200),
    offset: int = 0,
    asset_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(Asset).order_by(desc(Asset.created_at)).limit(limit).offset(offset)
    if asset_type:
        q = q.where(Asset.asset_type == asset_type)
    result = await db.execute(q)
    return [_out(a) for a in result.scalars().all()]


@router.get("/{asset_id}")
async def get_asset(asset_id: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Asset).where(Asset.id == asset_id))
    a = r.scalar_one_or_none()
    if not a:
        raise HTTPException(404, "Asset not found.")
    return _out(a)


@router.delete("/{asset_id}")
async def delete_asset(asset_id: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Asset).where(Asset.id == asset_id))
    a = r.scalar_one_or_none()
    if not a:
        raise HTTPException(404, "Asset not found.")
    import os
    if os.path.exists(a.file_path):
        os.remove(a.file_path)
    await db.delete(a)
    await db.commit()
    return {"message": "Deleted."}


def _out(a: Asset) -> dict:
    return {
        "id": a.id,
        "job_id": a.job_id,
        "asset_type": a.asset_type,
        "url": a.url,
        "width": a.width,
        "height": a.height,
        "duration_seconds": a.duration_seconds,
        "fps": a.fps,
        "file_size_bytes": a.file_size_bytes,
        "created_at": str(a.created_at),
    }
