from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from config import settings

# Pooled engine for the FastAPI app: one long-lived event loop, so pooled
# connections are reused safely across requests.
engine = create_async_engine(settings.database_url, pool_pre_ping=True, future=True)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


# Separate NullPool engine for Celery tasks (agents/*.py, tasks/*.py): each
# task runs via `asyncio.run()`, giving it a fresh event loop. A connection
# checked out from a pool in one task's loop fails with "Event loop is
# closed" if reused from the next task's loop — NullPool never holds a
# connection across calls, so this never happens.
celery_engine = create_async_engine(settings.database_url, pool_pre_ping=True, future=True, poolclass=NullPool)

celery_session_factory = async_sessionmaker(celery_engine, expire_on_commit=False)
