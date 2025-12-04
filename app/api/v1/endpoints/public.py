from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.database import get_db
from app.services import asset_service

router = APIRouter()


def format_asset_response(asset) -> dict:
    return asset.data


def format_asset_list_item(asset) -> dict:
    data = asset.data
    return {
        "id": str(asset.id),
        "asset_id": asset.asset_id,
        "asset_type": asset.asset_type,
        "status": asset.status,
        "basic_information": data.get("basic_information"),
        "overview": data.get("overview"),
        "eden_impact_summary": data.get("eden_impact_summary"),
        "deployment": data.get("deployment"),
    }


@router.get("/assets")
async def list_public_assets(
    q: Optional[str] = None,
    asset_type: Optional[str] = None,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    scaling_potential: Optional[str] = None,
    company_name: Optional[str] = None,
    creator_name: Optional[str] = None,
    climate_zone: Optional[str] = None,
    min_positive_impact: Optional[float] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="created_at", pattern="^(created_at|updated_at|eden_positive_impact_points)$"),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db)
):
    """
    Public browse endpoint - returns only approved assets.
    """
    assets, total = await asset_service.list_assets(
        db=db,
        q=q,
        asset_type=asset_type,
        category=category,
        subcategory=subcategory,
        scaling_potential=scaling_potential,
        company_name=company_name,
        creator_name=creator_name,
        climate_zone=climate_zone,
        min_positive_impact=min_positive_impact,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_dir=sort_dir,
        approved_only=True,
    )
    
    return {
        "items": [format_asset_list_item(a) for a in assets],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/assets/{asset_id}")
async def get_public_asset(
    asset_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a single approved asset by UUID.
    """
    asset = await asset_service.get_asset_by_id(db, asset_id)
    
    if not asset:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "not_found",
                    "message": f"Asset with id {asset_id} not found",
                    "details": {}
                }
            }
        )
    
    if asset.status != "approved":
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "not_found",
                    "message": f"Asset with id {asset_id} not found",
                    "details": {}
                }
            }
        )
    
    return format_asset_response(asset)
