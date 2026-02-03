#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ruff: noqa: E402, F403, I001, RUF100
import asyncio
import os
import sys

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import AsyncEngine

sys.path.append('../')

from backend.core import path_conf

if not os.path.exists(path_conf.ALEMBIC_Versions_DIR):
    os.makedirs(path_conf.ALEMBIC_Versions_DIR)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
from backend.common.model import MappedBase

# if add new app, do like this
from backend.app.admin.model import *  # noqa: F401
from backend.app.generator.model import *  # noqa: F401

target_metadata = MappedBase.metadata

# other values from the config, defined by the needs of env.py,
from backend.database.db_pg import SQLALCHEMY_DATABASE_URL

config.set_main_option('sqlalchemy.url', SQLALCHEMY_DATABASE_URL)


def include_object(object, name, type_, reflected, compare_to):
    """
    过滤 Alembic 自动生成迁移时要忽略的对象

    Args:
        object: 数据库对象
        name: 对象名称
        type_: 对象类型（table, column, index 等）
        reflected: 是否是从数据库反射得到的
        compare_to: 比较的目标对象

    Returns:
        True 表示包含该对象，False 表示忽略该对象
    """
    # 忽略 PostGIS/ParadeDB 的系统表
    if type_ == "table":
        # PostGIS 扩展的系统表
        postgis_tables = {
            'spatial_ref_sys',  # PostGIS 空间参考系统表
            'geometry_columns',  # PostGIS 几何列信息表
            'geography_columns',  # PostGIS 地理列信息表
            'raster_columns',  # PostGIS 栅格列信息表
            'raster_overviews',  # PostGIS 栅格概览表
        }

        # ParadeDB 扩展的系统表（如果有，可以继续添加）
        paradedb_tables = set()

        # 其他可能需要忽略的系统表
        system_tables = {
            'alembic_version',  # Alembic 版本表（通常已自动排除）
        }

        # 合并所有需要忽略的表
        excluded_tables = postgis_tables | paradedb_tables | system_tables

        if name in excluded_tables:
            return False

    return True


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option('sqlalchemy.url')
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = AsyncEngine(
        engine_from_config(
            config.get_section(config.config_ini_section),
            prefix='sqlalchemy.',
            poolclass=pool.NullPool,
            future=True,
        )
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
