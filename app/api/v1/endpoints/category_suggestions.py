from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional
from uuid import UUID
from datetime import datetime, date, timezone

from app.db.database import get_db
from app.core.security import get_current_user, require_admin
from app.models.user import User
from app.models.category_suggestion import CategorySuggestion
from app.models.asset import EdenAsset
from app.schemas.category_suggestion import (
    CategorySuggestionCreate,
    CategorySuggestionResponse,
    CategorySuggestionUpdate,
    CategorySuggestionListResponse
)

router = APIRouter()


async def check_duplicate(
    db: AsyncSession, 
    suggestion_type: str, 
    suggested_name: str, 
    primary_category: Optional[str] = None
) -> Optional[CategorySuggestion]:
    """Check if a similar suggestion already exists (pending or approved)"""
    query = select(CategorySuggestion).where(
        CategorySuggestion.suggestion_type == suggestion_type,
        func.lower(CategorySuggestion.suggested_name) == suggested_name.lower(),
        CategorySuggestion.status.in_(['pending', 'approved'])
    )
    
    if suggestion_type == 'subcategory' and primary_category:
        query = query.where(CategorySuggestion.primary_category == primary_category)
    
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def check_rate_limit(db: AsyncSession, user_id: UUID) -> tuple[int, int]:
    """Check how many pending suggestions user has (max 3) and today's total (max 5)"""
    # Count pending suggestions
    pending_query = select(func.count()).select_from(CategorySuggestion).where(
        CategorySuggestion.suggested_by_user_id == user_id,
        CategorySuggestion.status == 'pending'
    )
    pending_result = await db.execute(pending_query)
    pending_count = pending_result.scalar() or 0
    
    # Count today's suggestions
    today = date.today()
    today_query = select(func.count()).select_from(CategorySuggestion).where(
        CategorySuggestion.suggested_by_user_id == user_id,
        func.date(CategorySuggestion.created_at) == today
    )
    today_result = await db.execute(today_query)
    today_count = today_result.scalar() or 0
    
    return pending_count, today_count


async def get_suggestion_counts(db: AsyncSession) -> dict:
    """Get counts by status"""
    pending_query = select(func.count()).select_from(CategorySuggestion).where(CategorySuggestion.status == 'pending')
    approved_query = select(func.count()).select_from(CategorySuggestion).where(CategorySuggestion.status == 'approved')
    rejected_query = select(func.count()).select_from(CategorySuggestion).where(CategorySuggestion.status == 'rejected')
    
    pending_result = await db.execute(pending_query)
    approved_result = await db.execute(approved_query)
    rejected_result = await db.execute(rejected_query)
    
    return {
        'pending': pending_result.scalar() or 0,
        'approved': approved_result.scalar() or 0,
        'rejected': rejected_result.scalar() or 0,
    }


def build_suggestion_response(suggestion: CategorySuggestion) -> CategorySuggestionResponse:
    """Build response with related data"""
    asset_name = None
    if suggestion.asset:
        asset_name = suggestion.asset.data.get('basic_information', {}).get('asset_name')
    
    return CategorySuggestionResponse(
        id=suggestion.id,
        suggestion_type=suggestion.suggestion_type,
        primary_category=suggestion.primary_category,
        suggested_name=suggestion.suggested_name,
        reason=suggestion.reason,
        suggested_by_user_id=suggestion.suggested_by_user_id,
        suggested_by_email=suggestion.suggested_by.email if suggestion.suggested_by else None,
        asset_id=suggestion.asset_id,
        asset_name=asset_name,
        status=suggestion.status,
        admin_notes=suggestion.admin_notes,
        created_at=suggestion.created_at,
        reviewed_at=suggestion.reviewed_at,
        reviewed_by_user_id=suggestion.reviewed_by_user_id,
        reviewed_by_email=suggestion.reviewed_by.email if suggestion.reviewed_by else None
    )


@router.post("", response_model=CategorySuggestionResponse, status_code=201)
async def create_suggestion(
    suggestion: CategorySuggestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new category or subcategory suggestion"""
    # Check for duplicates
    duplicate = await check_duplicate(
        db, 
        suggestion.suggestion_type, 
        suggestion.suggested_name,
        suggestion.primary_category
    )
    if duplicate:
        raise HTTPException(
            status_code=400, 
            detail=f"A similar suggestion already exists with status: {duplicate.status}"
        )
    
    # Check rate limits
    pending_count, today_count = await check_rate_limit(db, current_user.id)
    if pending_count >= 3:
        raise HTTPException(
            status_code=400,
            detail="You have 3 pending suggestions. Please wait for them to be reviewed before submitting more."
        )
    if today_count >= 5:
        raise HTTPException(
            status_code=400,
            detail="You have reached the daily limit of 5 suggestions. Please try again tomorrow."
        )
    
    # Create suggestion
    db_suggestion = CategorySuggestion(
        suggestion_type=suggestion.suggestion_type,
        primary_category=suggestion.primary_category,
        suggested_name=suggestion.suggested_name,
        reason=suggestion.reason,
        suggested_by_user_id=current_user.id,
        asset_id=suggestion.asset_id,
        status='pending'
    )
    
    db.add(db_suggestion)
    await db.commit()
    await db.refresh(db_suggestion)
    
    # Load relationships
    query = select(CategorySuggestion).where(
        CategorySuggestion.id == db_suggestion.id
    ).options(
        selectinload(CategorySuggestion.suggested_by),
        selectinload(CategorySuggestion.reviewed_by),
        selectinload(CategorySuggestion.asset)
    )
    result = await db.execute(query)
    db_suggestion = result.scalar_one()
    
    return build_suggestion_response(db_suggestion)


@router.get("", response_model=CategorySuggestionListResponse)
async def list_suggestions(
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected"),
    suggestion_type: Optional[str] = Query(None, description="Filter by type: primary_category, subcategory"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """List all suggestions (admin only)"""
    query = select(CategorySuggestion).options(
        selectinload(CategorySuggestion.suggested_by),
        selectinload(CategorySuggestion.reviewed_by),
        selectinload(CategorySuggestion.asset)
    )
    
    if status:
        query = query.where(CategorySuggestion.status == status)
    if suggestion_type:
        query = query.where(CategorySuggestion.suggestion_type == suggestion_type)
    
    # Get total count
    count_query = select(func.count()).select_from(CategorySuggestion)
    if status:
        count_query = count_query.where(CategorySuggestion.status == status)
    if suggestion_type:
        count_query = count_query.where(CategorySuggestion.suggestion_type == suggestion_type)
    
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    # Get suggestions
    query = query.order_by(CategorySuggestion.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    suggestions = result.scalars().all()
    
    # Get counts
    counts = await get_suggestion_counts(db)
    
    return CategorySuggestionListResponse(
        suggestions=[build_suggestion_response(s) for s in suggestions],
        total=total,
        pending_count=counts['pending'],
        approved_count=counts['approved'],
        rejected_count=counts['rejected']
    )


@router.get("/my-suggestions", response_model=CategorySuggestionListResponse)
async def get_my_suggestions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's suggestions"""
    query = select(CategorySuggestion).where(
        CategorySuggestion.suggested_by_user_id == current_user.id
    ).options(
        selectinload(CategorySuggestion.suggested_by),
        selectinload(CategorySuggestion.reviewed_by),
        selectinload(CategorySuggestion.asset)
    ).order_by(CategorySuggestion.created_at.desc())
    
    result = await db.execute(query)
    suggestions = result.scalars().all()
    
    suggestion_responses = []
    for s in suggestions:
        response = build_suggestion_response(s)
        # Don't expose admin email to regular users
        response.reviewed_by_email = None
        suggestion_responses.append(response)
    
    return CategorySuggestionListResponse(
        suggestions=suggestion_responses,
        total=len(suggestions),
        pending_count=sum(1 for s in suggestions if s.status == 'pending'),
        approved_count=sum(1 for s in suggestions if s.status == 'approved'),
        rejected_count=sum(1 for s in suggestions if s.status == 'rejected')
    )


@router.patch("/{suggestion_id}", response_model=CategorySuggestionResponse)
async def update_suggestion(
    suggestion_id: UUID,
    update: CategorySuggestionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Approve or reject a suggestion (admin only)"""
    query = select(CategorySuggestion).where(
        CategorySuggestion.id == suggestion_id
    ).options(
        selectinload(CategorySuggestion.suggested_by),
        selectinload(CategorySuggestion.reviewed_by),
        selectinload(CategorySuggestion.asset)
    )
    result = await db.execute(query)
    suggestion = result.scalar_one_or_none()
    
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    if suggestion.status != 'pending':
        raise HTTPException(
            status_code=400, 
            detail=f"Suggestion has already been {suggestion.status}"
        )
    
    suggestion.status = update.status
    suggestion.admin_notes = update.admin_notes
    suggestion.reviewed_at = datetime.now(timezone.utc)
    suggestion.reviewed_by_user_id = current_user.id
    
    await db.commit()
    await db.refresh(suggestion)
    
    # Reload with relationships
    query = select(CategorySuggestion).where(
        CategorySuggestion.id == suggestion_id
    ).options(
        selectinload(CategorySuggestion.suggested_by),
        selectinload(CategorySuggestion.reviewed_by),
        selectinload(CategorySuggestion.asset)
    )
    result = await db.execute(query)
    suggestion = result.scalar_one()
    
    return build_suggestion_response(suggestion)


@router.delete("/{suggestion_id}", status_code=204)
async def delete_suggestion(
    suggestion_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete a suggestion (admin only)"""
    query = select(CategorySuggestion).where(CategorySuggestion.id == suggestion_id)
    result = await db.execute(query)
    suggestion = result.scalar_one_or_none()
    
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    await db.delete(suggestion)
    await db.commit()
    
    return None
