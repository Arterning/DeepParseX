# syntax=docker/dockerfile:1

# --- Builder Stage ---
FROM python:3.11-slim AS builder

# Install uv (your project uses it, it's fast)
RUN pip install uv

WORKDIR /app

# Copy only dependency definitions first for better layer caching
COPY pyproject.toml ./

# Install dependencies efficiently in one step and clean up
RUN uv pip install --system --no-cache --index-strategy unsafe-best-match --extra-index-url https://download.pytorch.org/whl/cpu --requirement pyproject.toml && \
    rm -rf /root/.cache /tmp/* /var/tmp/*

# Pre-download the model and save it to a known location
RUN mkdir -p /app/models && \
    python3 -c "from transformers import AutoTokenizer, AutoModel; \
    model_name = 'intfloat/multilingual-e5-small'; \
    tokenizer = AutoTokenizer.from_pretrained(model_name); \
    model = AutoModel.from_pretrained(model_name); \
    tokenizer.save_pretrained('/app/models'); \
    model.save_pretrained('/app/models')"

# --- Runtime Stage ---
FROM python:3.11-slim

# Install only runtime essentials and clean up in one layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash appuser
USER appuser
WORKDIR /home/appuser/app

# Copy installed dependencies from the builder stage's system python env
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy the pre-downloaded model
COPY --from=builder /app/models /home/appuser/app/models

# Copy your application code
# Important: Ensure the path matches your project structure relative to the Dockerfile
# Assuming Dockerfile is in 'meridian-ml-service' directory
COPY --chown=appuser:appuser ./src ./src
# Good practice, though likely not needed at runtime here
COPY --chown=appuser:appuser pyproject.toml ./

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    # Add src directory to Python path so modules can be found
    PYTHONPATH=/home/appuser/app:${PYTHONPATH} \
    # Fly.io sets PORT automatically, uvicorn will pick it up via $PORT in CMD
    # Default model from your config. Can be overridden via fly secrets.
    EMBEDDING_MODEL_NAME="/home/appuser/app/models" \
    # API_TOKEN should be provided via secrets at runtime, not in the Dockerfile
    # Set Hugging Face cache directory to somewhere writeable by appuser
    HF_HOME=/home/appuser/.cache/huggingface \
    TRANSFORMERS_CACHE=/home/appuser/.cache/huggingface/transformers \
    HF_HUB_CACHE=/home/appuser/.cache/huggingface/hub

# Ensure the cache directory exists and is owned by the app user
# This RUN command executes as root before switching back to appuser implicitly for CMD
USER root
RUN mkdir -p /home/appuser/.cache/huggingface && \
    chown -R appuser:appuser /home/appuser/.cache
USER appuser

# Expose the default port. Fly will map this.
EXPOSE 8080

# Run the application using uvicorn
# Update the import path to match your module structure
# Use $PORT which fly provides.
CMD ["uvicorn", "src.meridian_ml_service.main:app", "--host", "0.0.0.0", "--port", "8080"]