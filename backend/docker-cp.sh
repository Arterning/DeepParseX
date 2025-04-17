docker cp app/ fba_server:/fba/backend/
docker cp utils/ fba_server:fba/backend/
docker restart fba_server

docker cp app/ fba_celery:/fba/backend/
docker cp utils/ fba_celery:fba/backend/
docker restart fba_celery