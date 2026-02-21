#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
删除 alembic 表中的迁移记录脚本
用法: python scripts/clear_alembic.py
"""
import asyncio
import sys

from anyio import run

sys.path.append('../')

from sqlalchemy import delete, text

from backend.core.conf import settings
from backend.database.db_pg import async_engine


async def clear_alembic_records():
    """删除 alembic_version 表中的所有迁移记录"""
    try:
        async with async_engine.begin() as conn:
            # 删除 alembic_version 表中的所有记录
            result = await conn.execute(text("DELETE FROM alembic_version"))
            print(f"✅ 成功删除 {result.rowcount} 条 alembic 迁移记录")
            
            # 可选：显示表中的记录数（应该是0）
            count_result = await conn.execute(text("SELECT COUNT(*) FROM alembic_version"))
            count = count_result.scalar()
            print(f"📊 alembic_version 表中剩余记录数: {count}")
            
    except Exception as e:
        print(f"❌ 删除失败: {e}")
        sys.exit(1)


async def clear_specific_alembic_record(revision: str):
    """删除指定版本的 alembic 迁移记录"""
    try:
        async with async_engine.begin() as conn:
            # 删除指定版本的记录
            result = await conn.execute(
                text("DELETE FROM alembic_version WHERE version_num = :revision"),
                {"revision": revision}
            )
            print(f"✅ 成功删除版本 {revision} 的迁移记录，影响行数: {result.rowcount}")
            
    except Exception as e:
        print(f"❌ 删除失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        # 如果提供了参数，删除指定版本
        revision = sys.argv[1]
        print(f"🗑️  正在删除版本 {revision} 的 alembic 迁移记录...")
        asyncio.run(clear_specific_alembic_record(revision))
    else:
        # 否则删除所有记录
        print("⚠️  警告：这将删除所有 alembic 迁移记录！")
        print("如果只是想删除特定版本，请使用: python scripts/clear_alembic.py <revision_id>")
        
        confirm = input("确定要删除所有迁移记录吗？(yes/no): ")
        if confirm.lower() in ['yes', 'y']:
            print("🗑️  正在删除所有 alembic 迁移记录...")
            asyncio.run(clear_alembic_records())
        else:
            print("❌ 操作已取消")