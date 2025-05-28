nohup pdm run fastapi dev main.py --host 0.0.0.0 --port 8000 >> fba.log 2>&1 & 

pm2 start "pdm run fastapi dev main.py --host 0.0.0.0 --port 8000" --name lda-api

pm2 start "gunicorn backend.main:app --bind 0.0.0.0:8000" --name lda-api