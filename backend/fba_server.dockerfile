FROM python:3.10-slim

WORKDIR /fba

COPY backend /fba/backend
COPY deploy /fba/deploy

RUN mv backend/.env.docker /fba/backend/.env

# 修改软件源并添加非自由软件源（用于安装unrar）
RUN sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list.d/debian.sources \
    && sed -i 's|security.debian.org/debian-security|mirrors.ustc.edu.cn/debian-security|g' /etc/apt/sources.list.d/debian.sources \
    && sed -i 's/main/main non-free/g' /etc/apt/sources.list.d/debian.sources  # 添加non-free源

# 安装依赖，包括unrar
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc python3-dev libreoffice-writer vim unrar \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
RUN pip install --upgrade pip -i https://mirrors.aliyun.com/pypi/simple \
    && pip install -r backend/requirements.txt -i https://mirrors.aliyun.com/pypi/simple

ENV TZ=Asia/Shanghai

RUN mkdir -p /var/log/fastapi_server

COPY deploy/backend/fastapi_server.conf /etc/supervisor/conf.d/

EXPOSE 8001

CMD ["uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"]
