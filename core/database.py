from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with async_session() as session:
        yield session


@asynccontextmanager
async def db_session() -> AsyncGenerator[AsyncSession]:
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
