#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from minio import Minio
from backend.core.conf import settings


minio_client = Minio(
    settings.MINIO_URL,
    access_key=settings.ACCESS_KEY,
    secret_key=settings.SECRET_KEY,
    secure=False  # Change to True if Minio is using HTTPS
)
