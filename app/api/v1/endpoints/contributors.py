from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.database import get_db
from app.services import asset_service

router = APIRouter()


def format_asset_item(asset) -> dict:
    return {
        "id": str(asset.id),
        "asset_id": asset.asset_id,
        "asset_type": asset.asset_type,
        "data": asset.data,
    }


@router.get("/{contributor_id}/assets")
async def list_contributor_assets(
    contributor_id: str,
    status: Optional[str] = None,
    submission_status: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    List assets for a specific contributor.
    """
    assets, total = await asset_service.list_contributor_assets(
        db=db,
        contributor_id=contributor_id,
        status=status,
        submission_status=submission_status,
        page=page,
        page_size=page_size,
    )
    
    return {
        "items": [format_asset_item(a) for a in assets],
        "page": page,
        "page_size": page_size,
        "total": total,
    }
