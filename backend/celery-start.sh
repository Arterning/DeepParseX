#!/usr/bin/env bash

# work && beat
celery -A app.task.celery worker -l info -B --concurrency=10 -P eventlet

# flower
celery -A app.task.celery flower --port=8555 --basic-auth=admin:123456
