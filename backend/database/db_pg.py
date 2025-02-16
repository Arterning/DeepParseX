#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys

from typing import Annotated
from uuid import uuid4

from fastapi import Depends
from sqlalchemy import URL, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.common.log import log
from backend.common.model import MappedBase
from backend.core.conf import settings

def create_engine_and_session(url: str | URL):
    try:
        # 数据库引擎
        engine = create_async_engine(url, future=True, pool_pre_ping=True)
        log.success('数据库连接成功')
    except Exception as e:
        log.error('❌ 数据库链接失败 {}', e)
        sys.exit()
    else:
        db_session = async_sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
        return engine, db_session

SQLALCHEMY_DATABASE_URL = (
    f'postgresql+asyncpg://{settings.PG_USER}:{settings.PG_PASSWORD}@{settings.PG_HOST}:'
    f'{settings.PG_PORT}/{settings.PG_DATABASE}'
)

# SQLALCHEMY_DATABASE_URL = (
#     f'postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/fba'
# )

async_engine, async_db_session = create_engine_and_session(SQLALCHEMY_DATABASE_URL)


async def get_db() -> AsyncSession:
    """session 生成器"""
    session = async_db_session()
    try:
        yield session
    except Exception as se:
        await session.rollback()
        raise se
    finally:
        await session.close()


# Session Annotated
CurrentSession = Annotated[AsyncSession, Depends(get_db)]

async def execute_sql_file(session: AsyncSession, file_path: str):
    with open(file_path, 'r') as file:
        sql_commands = file.read().strip().split(';')  # 根据分号分割 SQL 语句
    for command in sql_commands:
        if command.strip():  # 确保不是空命令
            await session.execute(text(command))


async def create_table():
    """创建数据库表"""
    async with async_engine.begin() as coon:
        # await coon.execute(text("CREATE EXTENSION vector"))
        await coon.run_sync(MappedBase.metadata.create_all)
        result = await coon.execute(text("SELECT COUNT(*) FROM sys_user"))
        count = result.scalar()
        # 执行初始化脚本
        if count == 0:  # 如果没有数据，执行初始化脚本
            await execute_sql_file(coon, 'sql/init_test_data_pg.sql')
            log.info('初始化脚本执行成功')
        else:
            log.info('sys_user 表中已有数据，跳过初始化脚本的执行')


def uuid4_str() -> str:
    """数据库引擎 UUID 类型兼容性解决方案"""
    return str(uuid4())
