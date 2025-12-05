from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "EDEN Asset Library Backend"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/eden_assets"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/eden_assets"
    
    # AI Configuration
    USE_REAL_AI: bool = False  # Set to True when plugging in actual AI services
    AI_ENABLED: bool = False  # Legacy alias for USE_REAL_AI
    AI_SERVICE_URL: Optional[str] = None
    
    # JWT Authentication
    JWT_SECRET: str = "your-secret-key-change-in-production"
    JWT_EXPIRE_MINUTES: int = 60
    JWT_ALGORITHM: str = "HS256"
    
    # Initial admin user (for seeding)
    INITIAL_ADMIN_EMAIL: Optional[str] = None
    INITIAL_ADMIN_PASSWORD: Optional[str] = None
    
    # File uploads
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 50
    
    # R2/S3 Storage (for production)
    USE_R2_STORAGE: bool = False  # Set to True to use R2 instead of local storage
    R2_ACCOUNT_ID: Optional[str] = None
    R2_ACCESS_KEY_ID: Optional[str] = None
    R2_SECRET_ACCESS_KEY: Optional[str] = None
    R2_BUCKET_NAME: str = "eden-assets"
    R2_PUBLIC_URL: Optional[str] = None  # Optional custom domain for public access
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
