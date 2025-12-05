from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Literal, List
from datetime import datetime
from uuid import UUID


class CategorySuggestionCreate(BaseModel):
    suggestion_type: Literal['primary_category', 'subcategory']
    primary_category: Optional[str] = None  # Required if suggestion_type is 'subcategory'
    suggested_name: str = Field(..., min_length=3, max_length=100)
    reason: str = Field(..., min_length=10, max_length=500)
    asset_id: Optional[UUID] = None
    
    @model_validator(mode='after')
    def validate_subcategory_has_primary(self):
        if self.suggestion_type == 'subcategory' and not self.primary_category:
            raise ValueError('primary_category is required when suggesting a subcategory')
        
        if self.suggestion_type == 'primary_category' and self.primary_category:
            raise ValueError('primary_category should be null when suggesting a new primary category')
        
        return self
    
    @field_validator('suggested_name')
    @classmethod
    def clean_name(cls, v: str) -> str:
        return v.strip()


class CategorySuggestionResponse(BaseModel):
    id: UUID
    suggestion_type: str
    primary_category: Optional[str]
    suggested_name: str
    reason: str
    suggested_by_user_id: UUID
    suggested_by_email: Optional[str] = None
    asset_id: Optional[UUID]
    asset_name: Optional[str] = None
    status: str
    admin_notes: Optional[str]
    created_at: datetime
    reviewed_at: Optional[datetime]
    reviewed_by_user_id: Optional[UUID]
    reviewed_by_email: Optional[str] = None
    
    class Config:
        from_attributes = True


class CategorySuggestionUpdate(BaseModel):
    status: Literal['approved', 'rejected']
    admin_notes: Optional[str] = None


class CategorySuggestionListResponse(BaseModel):
    suggestions: List[CategorySuggestionResponse]
    total: int
    pending_count: int
    approved_count: int
    rejected_count: int
