# docker tag fba_server:latest fba_server:base and then build this dockerfile to create a new image with the changes.
FROM fba_server:base

WORKDIR /fba

COPY backend/app /fba/backend/app
COPY deploy /fba/deploy


