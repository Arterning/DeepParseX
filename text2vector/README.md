# 使用方式


# 构建 embedding 镜像
docker build -t embedding-api -f Dockerfile .


# 构建 rerank 镜像
docker build -t rerank-api -f Dockerfile.rerank .



## pm2 启动

默认启动embedding 模型，如果要启动rerank模型，修改pm2文件

```js
module.exports = {
  apps: [
    {
      name: 'rerank-api',
      script: '.venv/bin/uvicorn',
      args: 'main:app --host 0.0.0.0 --port 8004',
      interpreter: 'none',
      cwd: __dirname,
      autorestart: true,
      watch: false,
      max_memory_restart: '4G',
      env: {
        TRANSFORMERS_OFFLINE: '1',
        HF_DATASETS_OFFLINE: '1',
      },
    },
  ],
};

```