#!/bin/bash

# 参数1：自动生成alembic版本
if [ "$1" = "new" ]; then 
    if [ -d ".venv" ]; then
        uv run alembic revision --autogenerate
    else
        alembic revision --autogenerate
    fi
fi

# 参数2：升级alembic到最新版本
if [ "$1" = "run" ]; then
    if [ -d ".venv" ]; then
        uv run alembic upgrade head
    else
        alembic upgrade head
    fi
fi

# 参数3：删除版本文件并将alembic标记为base基准版本
if [ "$1" = "reset" ]; then
    # 删除alembic/versions下所有.py版本文件
    rm -rf alembic/versions/*.py
    # 检测虚拟环境并执行stamp base
    if [ -d ".venv" ]; then
        uv run alembic stamp base
    else
        alembic stamp base
    fi
fi