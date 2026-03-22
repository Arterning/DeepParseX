#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 create_table 方法
用于验证数据库表创建和初始化功能
"""
import asyncio
import sys
import os

sys.path.append('../')

from backend.database.db_pg import create_table
from backend.common.log import log


async def main():
    """主测试函数"""
    try:
        log.info('开始测试 create_table 方法...')
        await create_table()
        log.success('✅ create_table 方法执行成功！')
    except Exception as e:
        log.error(f'❌ create_table 方法执行失败: {e}')
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())