docker build -f backend/base.dockerfile -t fba_base_server .
docker build -f backend/backend.dockerfile -t fba_server .

docker build -t fba_server -f backend/fba_server.dockerfile .