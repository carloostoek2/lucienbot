"""
Alembic migration environment for Lucien Bot.
Reads DATABASE_URL from config.settings.bot_config and connects to the target database.
"""
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection
import sys
from pathlib import Path

# Ensure project root is on sys.path so models can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

from models.database import Base
from config.settings import bot_config

# Alembic Config object
config = context.config

# Set the SQLAlchemy URL from the project's DATABASE_URL
config.set_main_option("sqlalchemy.url", bot_config.DATABASE_URL)

# Configure logging from alembic.ini (if present)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support
target_metadata = Base.metadata


def include_object(object, name, type_, *args, **kwargs):
    """Exclude external tables not defined in our models (e.g., APScheduler jobs table)."""
    if type_ == "table" and name in ("apscheduler_jobs",):
        return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, include_object=include_object
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
