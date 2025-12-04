"""
Automated tests for EDEN Asset Library Backend API.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.database import Base, get_db
from app.models.user import User, UserRole
from app.core.security import get_password_hash, create_access_token


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(autouse=True, scope="function")
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def test_user():
    async with TestingSessionLocal() as session:
        user = User(
            name="Test User",
            email="test@example.com",
            password_hash=get_password_hash("testpassword"),
            role=UserRole.contributor
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def admin_user():
    async with TestingSessionLocal() as session:
        user = User(
            name="Admin User",
            email="admin@example.com",
            password_hash=get_password_hash("adminpassword"),
            role=UserRole.admin
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def auth_headers(test_user):
    token = create_access_token(data={"sub": str(test_user.id), "email": test_user.email, "role": test_user.role.value})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_auth_headers(admin_user):
    token = create_access_token(data={"sub": str(admin_user.id), "email": admin_user.email, "role": admin_user.role.value})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


MINIMAL_ASSET = {
    "asset_type": "physical",
    "basic_information": {
        "asset_name": "Test Asset",
        "category": "Energy"
    }
}

FULL_PHYSICAL_ASSET = {
    "asset_type": "physical",
    "basic_information": {
        "asset_name": "Solar Panel X100",
        "category": "Energy",
        "subcategory": "Solar",
        "short_summary": "High efficiency solar panel"
    },
    "contributor": {
        "name": "Test User",
        "email": "test@example.com",
        "contributor_id": "user_test"
    },
    "physical_configuration": {
        "unit_variants": [
            {
                "unit_name": "Standard",
                "dimensions": {"length": 100, "width": 50, "height": 5}
            }
        ]
    },
    "functional_io": {
        "inputs": [{"name": "Sunlight", "type": "energy"}],
        "outputs": [{"name": "Electricity", "type": "energy"}]
    }
}

FULL_PLAN_ASSET = {
    "asset_type": "plan",
    "basic_information": {
        "asset_name": "DIY Water Filter",
        "category": "Water",
        "short_summary": "Simple water filter plans"
    },
    "contributor": {
        "name": "Test User",
        "contributor_id": "user_test"
    },
    "plan_configuration": {
        "required_skill_level": "Beginner",
        "estimated_build_time_hours": 4
    }
}


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestCreateAsset:
    @pytest.mark.asyncio
    async def test_create_asset_minimal(self, client, auth_headers):
        """POST /assets creates a draft asset with minimal payload."""
        response = await client.post("/api/v1/assets", json=MINIMAL_ASSET, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["asset_type"] == "physical"
        assert data["basic_information"]["asset_name"] == "Test Asset"
        assert data["system_meta"]["status"] == "draft"
        assert "asset_id" in data

    @pytest.mark.asyncio
    async def test_create_asset_invalid_type(self, client, auth_headers):
        """POST /assets rejects invalid asset_type."""
        invalid_asset = {
            "asset_type": "invalid_type",
            "basic_information": {
                "asset_name": "Test",
                "category": "Energy"
            }
        }
        response = await client.post("/api/v1/assets", json=invalid_asset, headers=auth_headers)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_asset_missing_name(self, client, auth_headers):
        """POST /assets rejects missing asset_name."""
        invalid_asset = {
            "asset_type": "physical",
            "basic_information": {
                "category": "Energy"
            }
        }
        response = await client.post("/api/v1/assets", json=invalid_asset, headers=auth_headers)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_asset_missing_category(self, client, auth_headers):
        """POST /assets rejects missing category."""
        invalid_asset = {
            "asset_type": "physical",
            "basic_information": {
                "asset_name": "Test"
            }
        }
        response = await client.post("/api/v1/assets", json=invalid_asset, headers=auth_headers)
        assert response.status_code == 400


class TestUpdateAsset:
    @pytest.mark.asyncio
    async def test_update_asset_deep_merge(self, client, auth_headers):
        """PATCH /assets/:id performs deep merge for nested objects."""
        create_response = await client.post("/api/v1/assets", json=MINIMAL_ASSET, headers=auth_headers)
        asset_id = create_response.json()["asset_id"]
        
        get_response = await client.get("/api/v1/assets", headers=auth_headers)
        items = get_response.json()["items"]
        uuid = items[0]["id"]
        
        update_data = {
            "basic_information": {
                "short_summary": "Updated summary",
                "scaling_potential": "regional"
            },
            "overview": {
                "key_features": ["Feature 1", "Feature 2"]
            }
        }
        
        response = await client.patch(f"/api/v1/assets/{uuid}", json=update_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["basic_information"]["asset_name"] == "Test Asset"
        assert data["basic_information"]["short_summary"] == "Updated summary"
        assert data["basic_information"]["scaling_potential"] == "regional"
        assert data["overview"]["key_features"] == ["Feature 1", "Feature 2"]
        assert data["system_meta"]["version"] == "v2"


class TestGetAsset:
    @pytest.mark.asyncio
    async def test_get_asset_returns_stored_object(self, client, auth_headers):
        """GET /assets/:id returns the same object that was stored."""
        create_response = await client.post("/api/v1/assets", json=MINIMAL_ASSET, headers=auth_headers)
        assert create_response.status_code == 201
        created_data = create_response.json()
        
        list_response = await client.get("/api/v1/assets", headers=auth_headers)
        uuid = list_response.json()["items"][0]["id"]
        
        get_response = await client.get(f"/api/v1/assets/{uuid}")
        assert get_response.status_code == 200
        retrieved_data = get_response.json()
        
        assert retrieved_data["asset_id"] == created_data["asset_id"]
        assert retrieved_data["asset_type"] == created_data["asset_type"]
        assert retrieved_data["basic_information"]["asset_name"] == created_data["basic_information"]["asset_name"]

    @pytest.mark.asyncio
    async def test_get_asset_not_found(self, client):
        """GET /assets/:id returns 404 for non-existent asset."""
        response = await client.get("/api/v1/assets/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404


class TestListAssets:
    @pytest.mark.asyncio
    async def test_list_assets_filter_by_type(self, client, auth_headers):
        """GET /assets filters by asset_type."""
        await client.post("/api/v1/assets", json=MINIMAL_ASSET, headers=auth_headers)
        
        plan_asset = {
            "asset_type": "plan",
            "basic_information": {
                "asset_name": "Test Plan",
                "category": "Water"
            }
        }
        await client.post("/api/v1/assets", json=plan_asset, headers=auth_headers)
        
        response = await client.get("/api/v1/assets?asset_type=physical", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["asset_type"] == "physical"

    @pytest.mark.asyncio
    async def test_list_assets_filter_by_category(self, client, auth_headers):
        """GET /assets filters by category."""
        await client.post("/api/v1/assets", json=MINIMAL_ASSET, headers=auth_headers)
        
        water_asset = {
            "asset_type": "physical",
            "basic_information": {
                "asset_name": "Water Filter",
                "category": "Water"
            }
        }
        await client.post("/api/v1/assets", json=water_asset, headers=auth_headers)
        
        response = await client.get("/api/v1/assets?category=Energy", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["basic_information"]["category"] == "Energy"

    @pytest.mark.asyncio
    async def test_list_assets_pagination(self, client, auth_headers):
        """GET /assets pagination works correctly."""
        for i in range(5):
            asset = {
                "asset_type": "physical",
                "basic_information": {
                    "asset_name": f"Asset {i}",
                    "category": "Energy"
                }
            }
            await client.post("/api/v1/assets", json=asset, headers=auth_headers)
        
        response = await client.get("/api/v1/assets?page=1&page_size=2", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["page_size"] == 2


class TestSubmitAsset:
    @pytest.mark.asyncio
    async def test_submit_fails_missing_sections(self, client, auth_headers):
        """POST /assets/:id/submit fails if required sections are missing."""
        create_response = await client.post("/api/v1/assets", json=MINIMAL_ASSET, headers=auth_headers)
        
        list_response = await client.get("/api/v1/assets", headers=auth_headers)
        uuid = list_response.json()["items"][0]["id"]
        
        response = await client.post(f"/api/v1/assets/{uuid}/submit", headers=auth_headers)
        assert response.status_code == 400
        assert "error" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_submit_succeeds_with_required_sections(self, client, auth_headers):
        """POST /assets/:id/submit succeeds when required sections are present."""
        create_response = await client.post("/api/v1/assets", json=FULL_PHYSICAL_ASSET, headers=auth_headers)
        
        list_response = await client.get("/api/v1/assets", headers=auth_headers)
        uuid = list_response.json()["items"][0]["id"]
        
        response = await client.post(f"/api/v1/assets/{uuid}/submit", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["system_meta"]["status"] == "under_review"
        assert data["contributor"]["submission_status"] == "pending_review"


class TestApproveAsset:
    @pytest.mark.asyncio
    async def test_approve_updates_status(self, client, auth_headers, admin_auth_headers):
        """POST /assets/:id/approve updates status to approved."""
        create_response = await client.post("/api/v1/assets", json=FULL_PHYSICAL_ASSET, headers=auth_headers)
        
        list_response = await client.get("/api/v1/assets", headers=auth_headers)
        uuid = list_response.json()["items"][0]["id"]
        
        await client.post(f"/api/v1/assets/{uuid}/submit", headers=auth_headers)
        
        response = await client.post(f"/api/v1/assets/{uuid}/approve", json={
            "review_notes": "Looks good"
        }, headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["system_meta"]["status"] == "approved"
        assert data["contributor"]["submission_status"] == "approved"


class TestContributorAssets:
    @pytest.mark.asyncio
    async def test_list_contributor_assets(self, client, auth_headers, test_user):
        """GET /contributors/:contributor_id/assets returns only that contributor's assets."""
        asset1 = {
            "asset_type": "physical",
            "basic_information": {"asset_name": "Asset 1", "category": "Energy"},
        }
        asset2 = {
            "asset_type": "physical",
            "basic_information": {"asset_name": "Asset 2", "category": "Energy"},
        }
        
        await client.post("/api/v1/assets", json=asset1, headers=auth_headers)
        await client.post("/api/v1/assets", json=asset2, headers=auth_headers)
        
        response = await client.get(f"/api/v1/contributors/{test_user.id}/assets")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2


class TestFileAttachment:
    @pytest.mark.asyncio
    async def test_attach_file_url(self, client, auth_headers):
        """POST /assets/:id/files appends URLs under the chosen documentation field."""
        create_response = await client.post("/api/v1/assets", json=MINIMAL_ASSET, headers=auth_headers)
        
        list_response = await client.get("/api/v1/assets", headers=auth_headers)
        uuid = list_response.json()["items"][0]["id"]
        
        response = await client.post(f"/api/v1/assets/{uuid}/files", json={
            "target": "cad_file_urls",
            "url": "https://example.com/file.ifc"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "https://example.com/file.ifc" in data["documentation_uploads"]["cad_file_urls"]

    @pytest.mark.asyncio
    async def test_attach_file_invalid_target(self, client, auth_headers):
        """POST /assets/:id/files rejects invalid target."""
        create_response = await client.post("/api/v1/assets", json=MINIMAL_ASSET, headers=auth_headers)
        
        list_response = await client.get("/api/v1/assets", headers=auth_headers)
        uuid = list_response.json()["items"][0]["id"]
        
        response = await client.post(f"/api/v1/assets/{uuid}/files", json={
            "target": "invalid_target",
            "url": "https://example.com/file.pdf"
        }, headers=auth_headers)
        assert response.status_code == 400


class TestAIExtract:
    @pytest.mark.asyncio
    async def test_ai_extract_stub(self, client, auth_headers):
        """POST /assets/:id/ai-extract with USE_REAL_AI=false returns AIExtractionResponse."""
        create_response = await client.post("/api/v1/assets", json=MINIMAL_ASSET, headers=auth_headers)
        
        list_response = await client.get("/api/v1/assets", headers=auth_headers)
        uuid = list_response.json()["items"][0]["id"]
        
        response = await client.post(f"/api/v1/assets/{uuid}/ai-extract", json={
            "sources": {"use_uploaded_docs": True}
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # New response format: AIExtractionResponse
        assert "field_updates" in data
        assert "fields_prefilled" in data
        assert "sources_used" in data
        assert "notes_for_reviewer" in data
        
        # Verify sources_used contains at least stub data
        assert len(data["sources_used"]) > 0
        
        # Verify the asset was updated by fetching it
        asset_response = await client.get(f"/api/v1/assets/{uuid}", headers=auth_headers)
        asset_data = asset_response.json()
        assert asset_data["ai_assistance"]["prefill_status"] == "complete"


class TestReferenceData:
    @pytest.mark.asyncio
    async def test_get_asset_types(self, client):
        response = await client.get("/api/v1/reference/asset-types")
        assert response.status_code == 200
        assert "physical" in response.json()
        assert "plan" in response.json()
        assert "hybrid" in response.json()

    @pytest.mark.asyncio
    async def test_get_categories(self, client):
        response = await client.get("/api/v1/reference/categories")
        assert response.status_code == 200
        data = response.json()
        # New hierarchical structure with categories array
        assert "categories" in data
        assert len(data["categories"]) == 9  # 9 primary categories
        # Check that Energy and Heat is one of the primary categories
        primary_names = [cat["primary"] for cat in data["categories"]]
        assert "Energy and Heat" in primary_names
        # Check that each category has color and subcategories
        for cat in data["categories"]:
            assert "primary" in cat
            assert "subcategories" in cat
            assert "color" in cat

    @pytest.mark.asyncio
    async def test_get_subcategories_filtered(self, client):
        response = await client.get("/api/v1/reference/subcategories?category=Energy and Heat")
        assert response.status_code == 200
        subcategories = response.json()
        assert "Solar (PV panels, thermal collectors)" in subcategories
