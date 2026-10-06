"""
Alembic environment for WeatherVault.

The database URL comes from the app settings (DATABASE_URL in the environment or backend/.env),
not from alembic.ini, so migrations always target the same database as the running app.

Typical use, from backend/:
    alembic upgrade head                          # create or update the schema
    alembic revision --autogenerate -m "message"  # after changing app/models
A database created earlier by the app's create_all() already has the initial tables:
    alembic stamp 0001_initial_schema && alembic upgrade head
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.database import Base
import app.models.weather  # noqa: F401  (registers every table on Base.metadata)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
DATABASE_URL = settings.DATABASE_URL


def _configure(**kwargs) -> None:
    context.configure(
        target_metadata=target_metadata,
        compare_type=True,
        # SQLite cannot ALTER most things in place; batch mode rebuilds the table instead.
        render_as_batch=DATABASE_URL.startswith("sqlite"),
        **kwargs,
    )


def run_migrations_offline() -> None:
    """Emit the SQL instead of running it (alembic upgrade head --sql)."""
    _configure(url=DATABASE_URL, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    _configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = create_async_engine(DATABASE_URL, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
