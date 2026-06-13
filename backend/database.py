from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from config import settings

# NullPool: connections aren't held across calls, so a connection opened in
# one `asyncio.run()` (e.g. one Celery task) is never reused — and never
# fails with "Event loop is closed" — in a later `asyncio.run()` (the next
# task) on the same worker process.
engine = create_async_engine(settings.database_url, pool_pre_ping=True, future=True, poolclass=NullPool)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
