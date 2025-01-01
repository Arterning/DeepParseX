nohup pdm run fastapi dev main.py --host 0.0.0.0 >> fba.log 2>&1 & 
# pdm run fastapi dev main.py --host 0.0.0.0 --port 8001 --reload
# pdm run uvicorn main:app --host 0.0.0.0 --port 8001 --reload
nohup fastapi dev  /home/kemove/liboyu_code/backend/main.py --host 0.0.0.0 --port 8000 >> fba.log 2>&1  