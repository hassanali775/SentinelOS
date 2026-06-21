from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from shared.config.settings import settings

# Create the async engine with performance-tuned connection pooling
engine = create_async_engine(
    settings.POSTGRES_ASYNC_URI,
    echo=False,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10
)

# Centralized session factory for generating scoped async database sessions
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Declarative base that all ORM models will inherit from
Base = declarative_base()

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Dependency Provider for injecting scoped database sessions."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise