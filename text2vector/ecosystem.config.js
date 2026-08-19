module.exports = {
  apps: [
    {
      name: 'embedding-api',
      script: '.venv/bin/uvicorn',
      args: 'main:app --host 0.0.0.0 --port 8003',
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
