from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from app.core.config import settings


def fix_database_url_for_asyncpg(url: str) -> str:
    """
    Convert incompatible parameters for asyncpg compatibility.
    asyncpg doesn't support sslmode, channel_binding, and other libpq-specific params
    as query string parameters - they get passed as kwargs which asyncpg rejects.
    Instead, we strip them and use ssl=true for TLS connections.
    """
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    
    incompatible_params = ['sslmode', 'channel_binding', 'sslrootcert', 'sslcert', 'sslkey']
    has_ssl = False
    
    for param in incompatible_params:
        if param in query_params:
            if param == 'sslmode':
                sslmode = query_params[param][0]
                if sslmode in ('require', 'verify-ca', 'verify-full'):
                    has_ssl = True
            query_params.pop(param)
    
    if has_ssl:
        query_params['ssl'] = ['true']
    
    new_query = urlencode(query_params, doseq=True)
    new_parsed = parsed._replace(query=new_query)
    return urlunparse(new_parsed)


database_url = fix_database_url_for_asyncpg(settings.DATABASE_URL)
engine = create_async_engine(database_url, echo=False)
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
    Initialize database connection.
    
    NOTE: This function no longer auto-creates tables.
    Use Alembic migrations instead:
        alembic upgrade head
    
    This function is kept for any startup initialization that may be needed
    (e.g., connection pool warming, health checks).
    """
    # Connection verification is handled by the engine pool
    # No auto-create - use migrations instead
    pass
