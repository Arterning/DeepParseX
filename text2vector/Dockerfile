FROM python:3.10-slim

WORKDIR /app

# 1. 配置pip全局清华源，后续uv会继承pip源配置
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn \
    && pip install --no-cache-dir uv -i https://pypi.tuna.tsinghua.edu.cn/simple

# Install dependencies (cached layer)
COPY pyproject.toml uv.lock ./
# uv sync 指定清华源安装依赖，--index 参数强制使用国内源
RUN uv sync --frozen --no-dev --no-cache \
    --index https://pypi.tuna.tsinghua.edu.cn/simple \
    --extra-index-url https://mirrors.aliyun.com/pypi/simple/

# Copy application source
COPY main.py chunker.py ./

# Copy model files (expected at models/BAAI/bge-m3/)
COPY models/ ./models/

# Point to the local model path; override at runtime if needed
ENV EMBEDDING_MODEL=models/BAAI/bge-m3
ENV RERANK_MODEL=models/BAAI/bge-reranker-v2-m3

# HuggingFace国内镜像 + 完全禁止联网下载模型
ENV HF_ENDPOINT=https://hf-mirror.com
ENV TRANSFORMERS_OFFLINE=1
ENV HF_DATASETS_OFFLINE=1

EXPOSE 8003

CMD [".venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]