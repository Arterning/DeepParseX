#!/bin/bash

rm -rf alembic/versions/*.py

if [ -d ".venv" ]; then
    uv run alembic stamp base
else
    alembic stamp base
fi