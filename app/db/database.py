import ssl
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from app.core.config import settings


def fix_database_url_for_asyncpg(url: str) -> tuple[str, bool]:
    """
    Remove incompatible parameters for asyncpg compatibility.
    asyncpg doesn't support sslmode, channel_binding, and other libpq-specific params
    as query string parameters - they get passed as kwargs which asyncpg rejects.
    Returns the cleaned URL and whether SSL should be enabled.
    """
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    
    incompatible_params = ['sslmode', 'channel_binding', 'sslrootcert', 'sslcert', 'sslkey', 'ssl']
    has_ssl = False
    
    for param in incompatible_params:
        if param in query_params:
            if param == 'sslmode':
                sslmode = query_params[param][0]
                if sslmode in ('require', 'verify-ca', 'verify-full'):
                    has_ssl = True
            elif param == 'ssl':
                if query_params[param][0].lower() == 'true':
                    has_ssl = True
            query_params.pop(param)
    
    new_query = urlencode(query_params, doseq=True)
    new_parsed = parsed._replace(query=new_query)
    return urlunparse(new_parsed), has_ssl


database_url, needs_ssl = fix_database_url_for_asyncpg(settings.DATABASE_URL)

# Create SSL context for asyncpg if needed
connect_args = {}
if needs_ssl:
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    connect_args["ssl"] = ssl_context

engine = create_async_engine(database_url, echo=False, connect_args=connect_args)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """
    Initialize database connection and seed admin user.
    
    NOTE: This function no longer auto-creates tables.
    Use Alembic migrations instead:
        alembic upgrade head
    
    This function seeds an admin user on startup if one doesn't exist.
    Uses INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD env vars if set,
    otherwise uses default admin credentials.
    """
    from sqlalchemy import select
    from app.models.user import User
    from app.core.security import get_password_hash
    
    # Default admin credentials (can be overridden by env vars)
    admin_email = settings.INITIAL_ADMIN_EMAIL or "camara@mastermindingeden.com"
    admin_password = settings.INITIAL_ADMIN_PASSWORD or "EdenAdmin2024!"
    
    async with async_session_maker() as session:
        # Check if admin already exists
        result = await session.execute(select(User).where(User.email == admin_email))
        existing_admin = result.scalar_one_or_none()
        
        if existing_admin is None:
            admin_user = User(
                name="Admin",
                email=admin_email,
                password_hash=get_password_hash(admin_password),
                role="admin",
            )
            session.add(admin_user)
            await session.commit()
            print(f"Admin user created: {admin_email}")
