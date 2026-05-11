import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from backend.config import get_settings
from backend.db.session import Base

# ── Alembic Config ────────────────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Models ────────────────────────────────────────────
import backend.models.user        # noqa: F401
import backend.models.org         # noqa: F401
import backend.models.membership  # noqa: F401
import backend.models.invite      # noqa: F401
import backend.models.campaign    # noqa: F401
import backend.models.session     # noqa: F401
import backend.models.character   # noqa: F401
import backend.models.campaign_extras  # noqa: F401


target_metadata = Base.metadata

# ── Override the DB URL from settings ────────────────────────────────────────
settings = get_settings()


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (outputs raw SQL)."""
    context.configure(
        url=settings.async_database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations with a live async DB connection."""
    connectable = create_async_engine(settings.async_database_url)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())