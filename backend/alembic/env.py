from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, text
from alembic import context
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import Base
import app.models  # noqa: F401 - register every mapped table for migration metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    """Read only the migration dependency, without constructing app Settings.

    Alembic runs before the API process.  Requiring authentication, mail, or
    AI configuration here can block a perfectly valid schema migration.
    """

    value = os.environ.get("DATABASE_URL", "").strip()
    if value:
        return value
    value = config.get_main_option("sqlalchemy.url").strip()
    if value:
        return value
    raise RuntimeError("DATABASE_URL is required to run database migrations")

def run_migrations_offline() -> None:
    url = _database_url()
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = _database_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
