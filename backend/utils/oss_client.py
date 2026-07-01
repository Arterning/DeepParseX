#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import io

from minio import Minio

from backend.core.conf import settings


minio_client = Minio(
    settings.MINIO_URL,
    access_key=settings.ACCESS_KEY,
    secret_key=settings.SECRET_KEY,
    secure=False  # Change to True if Minio is using HTTPS
)


async def put_object(
    bucket_name: str,
    object_name: str,
    data: bytes,
    content_type: str = 'application/octet-stream',
):
    """异步上传 bytes 到 MinIO"""
    def _sync():
        file_stream = io.BytesIO(data)
        minio_client.put_object(
            bucket_name, object_name, file_stream, len(data), content_type,
        )
    await asyncio.to_thread(_sync)
