

## Install venv
uv venv
uv pip install pyproject.toml

## Run App

uv run uvicorn src.meridian_ml_service.main:app --host 0.0.0.0 --port 8080

# Env file
set model name is BAAI/bge-large-zh-v1.5