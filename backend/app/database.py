"""
Async SQLAlchemy database engine and session management.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

_engine_kwargs: dict = {"echo": settings.DEBUG}

if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite needs special handling for async
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _engine_kwargs.update(pool_size=10, max_overflow=20, pool_pre_ping=True)

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """Dependency that provides an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
