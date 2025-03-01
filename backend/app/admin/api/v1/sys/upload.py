#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from fastapi import APIRouter

from backend.common.response.response_schema import response_base
from backend.app.admin.service.upload_service import upload_service
import os
from fastapi import File, UploadFile
from pathlib import Path
from backend.common.log import log
import os
router = APIRouter()


def get_file_extension(filename: str) -> str:
    return os.path.splitext(filename)[1][1:]

def is_zip_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ['.zip']

def is_excel_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ['.xls', '.xlsx']

def is_csv_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ['.csv']

def is_pdf_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ['.pdf']

def is_picture_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ['.jpeg', '.jpg', '.png']

def is_media_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ['.mp4', '.mp3', '.flv', '.wav']

def is_text_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ['.txt', '.host', '.config',
                                             '.c', '.cpp', '.java', '.py', 'js', '.ts', '.rb', '.go']
def is_email_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ['.eml']


file_type_handlers = {
    'excel': is_excel_file,
    'csv': is_csv_file,
    'picture': is_picture_file,
    'media': is_media_file,
    'text': is_text_file,
    'email': is_email_file,
    'pdf': is_pdf_file,
    'zip': is_zip_file
}
def get_file_type(file_name: str):
    for file_type, handler in file_type_handlers.items():
        if handler(file_name):
            return file_type
    return 'text'

@router.post("/", summary='上传文件')
async def upload_file(file: UploadFile = File(...)):
    log.info('上传文件')
    filename = file.filename
    resp = {"filename": file.filename}
    if is_excel_file(filename):
        log.info("read excel")
        await upload_service.read_excel(file)
        return response_base.success(data=resp)
    
    if is_csv_file(filename):
        log.info("read csv")
        await upload_service.read_text(file)
        return response_base.success(data=resp)
    
    if is_picture_file(filename):
        log.info("read picture")
        await upload_service.read_picture(file)
        return response_base.success(data=resp)

    if is_media_file(filename):
        log.info("read media")
        await upload_service.read_media(file)
        return response_base.success(data=resp)

    if is_text_file(filename):
        log.info("read text")
        await upload_service.read_text(file)
        return response_base.success(data=resp)

    if is_email_file(filename):
        log.info("read email")
        await upload_service.read_email(file)
        return response_base.success(data=resp)

    if is_pdf_file(filename):
        log.info("read pdf")
        await upload_service.read_pdf(file)
        return response_base.success(data=resp)
    
    if is_zip_file(filename):
        log.info("read zip")
        await upload_service.read_zip(file)
        return response_base.success(data=resp)

    log.info("no match, read text")
    await upload_service.read_text(file)
    return response_base.success(data=resp)
