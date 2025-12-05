from fastapi import APIRouter

from app.api.v1.endpoints import assets, auth, contributors, reference, public, health, category_suggestions

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(auth.router, tags=["Authentication"])
api_router.include_router(assets.router, prefix="/assets", tags=["Assets"])
api_router.include_router(contributors.router, prefix="/contributors", tags=["Contributors"])
api_router.include_router(reference.router, prefix="/reference", tags=["Reference Data"])
api_router.include_router(public.router, prefix="/public", tags=["Public"])
api_router.include_router(category_suggestions.router, prefix="/category-suggestions", tags=["Category Suggestions"])
