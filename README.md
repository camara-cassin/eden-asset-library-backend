# EDEN Asset Library Backend

Backend API for the EDEN Asset Library - Store, manage, and query assets that conform to the EdenAsset JSON schema.

## Tech Stack

- **Runtime**: Python 3.11+
- **Framework**: FastAPI
- **Database**: PostgreSQL with JSONB
- **Validation**: Pydantic + jsonschema
- **API Documentation**: OpenAPI 3 with Swagger UI

## Features

- Full CRUD operations for EdenAsset objects
- Multi-step onboarding with draft saves
- Workflow management (submit, approve, reject)
- Query and filtering with pagination
- Reference data endpoints for UI dropdowns
- AI prefill stub (ready for future AI integration)
- File URL attachment support
- JWT authentication with role-based access control
- User roles: admin, contributor, viewer

## Setup

### Prerequisites

- Python 3.11 or higher
- PostgreSQL 14 or higher
- Poetry (Python package manager)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/camara-cassin/eden-asset-library-backend.git
cd eden-asset-library-backend
```

2. Install dependencies:
```bash
poetry install
```

3. Create a PostgreSQL database:
```bash
createdb eden_assets
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL async connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/eden_assets` |
| `DATABASE_URL_SYNC` | PostgreSQL sync connection string | `postgresql://postgres:postgres@localhost:5432/eden_assets` |
| `AI_ENABLED` | Enable AI extraction features | `false` |
| `AI_SERVICE_URL` | URL of AI microservice (when enabled) | `None` |
| `JWT_SECRET` | Secret key for JWT token signing (REQUIRED in production) | `your-secret-key-change-in-production` |
| `JWT_EXPIRE_MINUTES` | JWT token expiration time in minutes | `60` |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `INITIAL_ADMIN_EMAIL` | Email for initial admin user (optional, for seeding) | `None` |
| `INITIAL_ADMIN_PASSWORD` | Password for initial admin user (optional, for seeding) | `None` |

**IMPORTANT**: In production, you MUST set `JWT_SECRET` to a secure random value. The default value is insecure.

### Database Setup

**Important**: The database tables are NOT auto-created. You must run migrations first.

1. Run database migrations:
```bash
# Set DATABASE_URL_SYNC environment variable or update alembic.ini
export DATABASE_URL_SYNC=postgresql://postgres:postgres@localhost:5432/eden_assets

# Run migrations
poetry run alembic upgrade head
```

2. (Optional) Seed the database with example assets:
```bash
poetry run python scripts/seed.py
```

#### Migration Commands

```bash
# View current migration status
poetry run alembic current

# Create a new migration (after model changes)
poetry run alembic revision --autogenerate -m "description"

# Upgrade to latest
poetry run alembic upgrade head

# Downgrade one revision
poetry run alembic downgrade -1

# Downgrade to base (empty database)
poetry run alembic downgrade base
```

### Running the Server

Development mode with auto-reload:
```bash
poetry run fastapi dev app/main.py
```

Production mode:
```bash
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Running Tests

```bash
poetry run pytest tests/ -v
```

## API Documentation

Once the server is running, access the interactive API documentation at:

- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

## API Endpoints

### Health Check
- `GET /api/v1/health` - Health check with build info

### Authentication
- `POST /api/v1/auth/login` - Login with email/password, returns JWT token
- `GET /api/v1/auth/me` - Get current user info (requires authentication)

### Assets (Protected - requires authentication)
- `POST /api/v1/assets` - Create a new asset (auto-sets contributor from current user)
- `GET /api/v1/assets` - List assets (contributors see only their own, admins see all)
- `GET /api/v1/assets/:id` - Get single asset (authorization check)
- `PATCH /api/v1/assets/:id` - Update asset (only owner or admin)
- `DELETE /api/v1/assets/:id` - Soft delete asset (only owner or admin)

### Workflow
- `POST /api/v1/assets/:id/submit` - Submit for review (requires authentication)
- `POST /api/v1/assets/:id/approve` - Approve asset (admin only)
- `POST /api/v1/assets/:id/reject` - Reject asset (admin only)

### Files
- `POST /api/v1/assets/:id/files` - Attach file URL

### AI Extraction
- `POST /api/v1/assets/:id/ai-extract` - Trigger AI extraction (stub mode)

### Contributors
- `GET /api/v1/contributors/:contributor_id/assets` - List contributor's assets

### Reference Data
- `GET /api/v1/reference/asset-types`
- `GET /api/v1/reference/categories`
- `GET /api/v1/reference/subcategories`
- `GET /api/v1/reference/scaling-potentials`
- `GET /api/v1/reference/license-types`
- `GET /api/v1/reference/climate-zones`
- `GET /api/v1/reference/submission-statuses`
- `GET /api/v1/reference/system-statuses`

### Public (Approved Only)
- `GET /api/v1/public/assets` - Browse approved assets
- `GET /api/v1/public/assets/:id` - Get approved asset

## Example API Requests

### Create a Draft Asset

```bash
curl -X POST http://localhost:8000/api/v1/assets \
  -H "Content-Type: application/json" \
  -d '{
    "asset_type": "physical",
    "basic_information": {
      "asset_name": "Solar Roof Tile X100",
      "category": "Energy",
      "short_summary": "Modular solar roof tile system"
    },
    "contributor": {
      "name": "Jane Scout",
      "email": "jane@example.org",
      "contributor_id": "user_123"
    }
  }'
```

### Update Asset (Partial)

```bash
curl -X PATCH http://localhost:8000/api/v1/assets/{uuid} \
  -H "Content-Type: application/json" \
  -d '{
    "basic_information": {
      "short_summary": "Updated summary",
      "scaling_potential": "regional"
    },
    "overview": {
      "key_features": ["High efficiency", "Easy installation"]
    }
  }'
```

### Submit for Review

```bash
curl -X POST http://localhost:8000/api/v1/assets/{uuid}/submit
```

### Approve Asset

```bash
curl -X POST http://localhost:8000/api/v1/assets/{uuid}/approve \
  -H "Content-Type: application/json" \
  -d '{
    "reviewer_id": "admin_42",
    "review_notes": "Looks good"
  }'
```

### Search Assets

```bash
curl "http://localhost:8000/api/v1/assets?q=solar&category=Energy&page=1&page_size=20"
```

### Attach File URL

```bash
curl -X POST http://localhost:8000/api/v1/assets/{uuid}/files \
  -H "Content-Type: application/json" \
  -d '{
    "target": "cad_file_urls",
    "url": "https://example.com/files/asset123.ifc"
  }'
```

### Call AI Extraction Stub

```bash
curl -X POST http://localhost:8000/api/v1/assets/{uuid}/ai-extract \
  -H "Content-Type: application/json" \
  -d '{
    "sources": {
      "use_uploaded_docs": true,
      "extra_doc_urls": ["https://example.com/spec-sheet.pdf"]
    }
  }'
```

## Project Structure

```
eden-asset-library-backend/
├── alembic/                       # Database migrations
│   ├── versions/                  # Migration files
│   │   └── c842fc4eccb4_create_eden_assets_table.py
│   └── env.py                     # Alembic configuration
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── assets.py      # Asset CRUD and workflow
│   │       │   ├── contributors.py # Contributor endpoints
│   │       │   ├── health.py      # Health check
│   │       │   ├── public.py      # Public browse endpoints
│   │       │   └── reference.py   # Reference data
│   │       └── router.py          # API router
│   ├── core/
│   │   └── config.py              # Configuration settings
│   ├── db/
│   │   └── database.py            # Database connection
│   ├── models/
│   │   └── asset.py               # SQLAlchemy models
│   ├── schemas/
│   │   ├── asset.py               # Pydantic schemas
│   │   └── eden_asset.schema.json # JSON schema
│   ├── services/
│   │   ├── asset_service.py       # Business logic
│   │   └── validation.py          # Validation logic
│   └── main.py                    # FastAPI application
├── scripts/
│   └── seed.py                    # Database seeding
├── tests/
│   └── test_api.py                # API tests
├── .env.example                   # Environment template
├── alembic.ini                    # Alembic configuration
├── openapi.json                   # OpenAPI 3 specification
├── pyproject.toml                 # Poetry configuration
└── README.md                      # This file
```

## License

MIT
