from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.category_suggestion import CategorySuggestion
from app.schemas.category_suggestion import CategorySuggestionCreate, CategorySuggestionUpdate
from datetime import datetime, date, timezone
from typing import Optional, List, Tuple
from uuid import UUID


class CategorySuggestionService:
    
    @staticmethod
    def check_duplicate(db: Session, suggestion_type: str, suggested_name: str, primary_category: Optional[str] = None) -> Optional[CategorySuggestion]:
        """Check if a similar suggestion already exists (pending or approved)"""
        query = db.query(CategorySuggestion).filter(
            CategorySuggestion.suggestion_type == suggestion_type,
            func.lower(CategorySuggestion.suggested_name) == suggested_name.lower(),
            CategorySuggestion.status.in_(['pending', 'approved'])
        )
        
        if suggestion_type == 'subcategory' and primary_category:
            query = query.filter(CategorySuggestion.primary_category == primary_category)
        
        return query.first()
    
    @staticmethod
    def check_rate_limit(db: Session, user_id: UUID) -> Tuple[int, int]:
        """Check how many pending suggestions user has (max 3) and today's total (max 5)"""
        pending_count = db.query(CategorySuggestion).filter(
            CategorySuggestion.suggested_by_user_id == user_id,
            CategorySuggestion.status == 'pending'
        ).count()
        
        today = date.today()
        today_count = db.query(CategorySuggestion).filter(
            CategorySuggestion.suggested_by_user_id == user_id,
            func.date(CategorySuggestion.created_at) == today
        ).count()
        
        return pending_count, today_count
    
    @staticmethod
    def create_suggestion(db: Session, suggestion: CategorySuggestionCreate, user_id: UUID) -> CategorySuggestion:
        """Create a new category suggestion"""
        
        # Check for duplicates
        duplicate = CategorySuggestionService.check_duplicate(
            db, 
            suggestion.suggestion_type, 
            suggestion.suggested_name,
            suggestion.primary_category
        )
        if duplicate:
            raise ValueError(f"A similar suggestion already exists with status: {duplicate.status}")
        
        # Check rate limits
        pending_count, today_count = CategorySuggestionService.check_rate_limit(db, user_id)
        if pending_count >= 3:
            raise ValueError("You have 3 pending suggestions. Please wait for them to be reviewed before submitting more.")
        if today_count >= 5:
            raise ValueError("You have reached the daily limit of 5 suggestions. Please try again tomorrow.")
        
        # Create suggestion
        db_suggestion = CategorySuggestion(
            suggestion_type=suggestion.suggestion_type,
            primary_category=suggestion.primary_category,
            suggested_name=suggestion.suggested_name,
            reason=suggestion.reason,
            suggested_by_user_id=user_id,
            asset_id=suggestion.asset_id,
            status='pending'
        )
        
        db.add(db_suggestion)
        db.commit()
        db.refresh(db_suggestion)
        
        return db_suggestion
    
    @staticmethod
    def get_suggestions(
        db: Session, 
        status: Optional[str] = None,
        suggestion_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[CategorySuggestion], int]:
        """Get suggestions with optional filtering"""
        query = db.query(CategorySuggestion)
        
        if status:
            query = query.filter(CategorySuggestion.status == status)
        if suggestion_type:
            query = query.filter(CategorySuggestion.suggestion_type == suggestion_type)
        
        total = query.count()
        suggestions = query.order_by(CategorySuggestion.created_at.desc()).offset(skip).limit(limit).all()
        
        return suggestions, total
    
    @staticmethod
    def get_suggestion_counts(db: Session) -> dict:
        """Get counts by status"""
        return {
            'pending': db.query(CategorySuggestion).filter(CategorySuggestion.status == 'pending').count(),
            'approved': db.query(CategorySuggestion).filter(CategorySuggestion.status == 'approved').count(),
            'rejected': db.query(CategorySuggestion).filter(CategorySuggestion.status == 'rejected').count(),
        }
    
    @staticmethod
    def get_user_suggestions(db: Session, user_id: UUID) -> List[CategorySuggestion]:
        """Get all suggestions by a specific user"""
        return db.query(CategorySuggestion).filter(
            CategorySuggestion.suggested_by_user_id == user_id
        ).order_by(CategorySuggestion.created_at.desc()).all()
    
    @staticmethod
    def update_suggestion(
        db: Session, 
        suggestion_id: UUID, 
        update: CategorySuggestionUpdate,
        admin_user_id: UUID
    ) -> CategorySuggestion:
        """Approve or reject a suggestion"""
        suggestion = db.query(CategorySuggestion).filter(CategorySuggestion.id == suggestion_id).first()
        if not suggestion:
            raise ValueError("Suggestion not found")
        
        if suggestion.status != 'pending':
            raise ValueError(f"Suggestion has already been {suggestion.status}")
        
        suggestion.status = update.status
        suggestion.admin_notes = update.admin_notes
        suggestion.reviewed_at = datetime.now(timezone.utc)
        suggestion.reviewed_by_user_id = admin_user_id
        
        db.commit()
        db.refresh(suggestion)
        
        return suggestion
    
    @staticmethod
    def delete_suggestion(db: Session, suggestion_id: UUID) -> bool:
        """Delete a suggestion"""
        suggestion = db.query(CategorySuggestion).filter(CategorySuggestion.id == suggestion_id).first()
        if not suggestion:
            return False
        
        db.delete(suggestion)
        db.commit()
        return True
