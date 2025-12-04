from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "EDEN Asset Library Backend"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/eden_assets"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/eden_assets"
    
    AI_ENABLED: bool = False
    AI_SERVICE_URL: Optional[str] = None
    
    # JWT Authentication
    JWT_SECRET: str = "your-secret-key-change-in-production"
    JWT_EXPIRE_MINUTES: int = 60
    JWT_ALGORITHM: str = "HS256"
    
    # Initial admin user (for seeding)
    INITIAL_ADMIN_EMAIL: Optional[str] = None
    INITIAL_ADMIN_PASSWORD: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
