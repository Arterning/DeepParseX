#!/bin/bash
if [ "$1" = "builder" ]; then
    echo "正在构建后端基础镜像..."
    docker build -t fba_server_builder -f backend/fba_server.dockerfile .
else
    echo "正在构建后端镜像..."
    docker build -t fba_server -f backend/Dockerfile .
fi

# 构建成功则清理镜像，失败则不执行
[ $? -eq 0 ] && docker image prune