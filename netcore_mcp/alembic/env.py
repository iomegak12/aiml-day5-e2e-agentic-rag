"""Alembic environment for the itsm schema (async engine, URL from DATABASE_URL, version table in itsm)."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from netcore_mcp.config import get_settings
from netcore_mcp.models import SCHEMA, Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
OPTIONS = {"version_table_schema": SCHEMA, "include_schemas": True,
           # only this schema belongs to this chain (the API owns public)
           "include_name": lambda name, type_, _parent: type_ != "schema" or name == SCHEMA}


def run_migrations_offline() -> None:
    context.configure(url=get_settings().database_url, target_metadata=target_metadata, literal_binds=True,
                      dialect_opts={"paramstyle": "named"}, **OPTIONS)
    with context.begin_transaction():
        context.run_migrations()


def _run(connection) -> None:
    connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))  # the version table lives in it
    context.configure(connection=connection, target_metadata=target_metadata, **OPTIONS)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(get_settings().database_url)
    async with engine.begin() as connection:
        await connection.run_sync(_run)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
