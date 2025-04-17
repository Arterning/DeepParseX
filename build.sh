# docker build -f backend/base.dockerfile -t fba_base_server .
# docker build -f backend/backend.dockerfile -t fba_server .
# docker build -f backend/fba_db.dockerfile -t fba_db .

docker build -t fba_celery -f backend/celery.dockerfile .
docker build -t fba_server -f backend/fba_server.dockerfile .
docker image prune