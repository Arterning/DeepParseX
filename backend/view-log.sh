docker exec -it fba_server tail -f /var/log/fastapi_server/gunicorn_error.log

# docker exec -it fba_celery tail -f /var/log/celery/fba_celery_worker.log