from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    verify_password,
    create_access_token,
    get_current_user,
)
from app.db.database import get_db
from app.models.user import User
from app.core.security import get_password_hash
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse, SignupRequest, SignupResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and return JWT token.
    """
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalar_one_or_none()
    
    if user is None or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value
        },
        expires_delta=timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    )
    
    return TokenResponse(access_token=access_token)


@router.post("/signup", response_model=SignupResponse)
async def signup(
    signup_data: SignupRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user account.
    
    - Email must be unique
    - Password must be at least 8 characters
    - New users are always created with role = "contributor"
    - Returns JWT token and user info on success
    """
    result = await db.execute(select(User).where(User.email == signup_data.email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )
    
    name = signup_data.name if signup_data.name else signup_data.email.split("@")[0]
    
    new_user = User(
        name=name,
        email=signup_data.email,
        password_hash=get_password_hash(signup_data.password),
        role="contributor",
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    access_token = create_access_token(
        data={
            "sub": str(new_user.id),
            "email": new_user.email,
            "role": new_user.role.value
        },
        expires_delta=timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    )
    
    return SignupResponse(
        access_token=access_token,
        user=UserResponse.model_validate(new_user)
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user.
    """
    return UserResponse.model_validate(current_user)
