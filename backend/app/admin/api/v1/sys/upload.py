#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from fastapi import APIRouter

from backend.app.admin.schema.doc import CreateSysDocParam, UpdateSysDocParam
from backend.app.admin.schema.doc_data import CreateSysDocDataParam
from backend.app.admin.service.doc_service import sys_doc_service
from backend.common.response.response_schema import response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.utils.doc_utils import post_pdf_recog, post_imagesocr_recog, post_audios_recog, post_emails_recog
import os
from fastapi import File, UploadFile
from pathlib import Path
import pandas as pd
import numpy as np
import asyncio
from io import BytesIO
from backend.common.log import log
import traceback
import zipfile

router = APIRouter()

# 定义上传文件保存的目录
UPLOAD_DIRECTORY = "uploads"

# 创建上传文件的目录，如果不存在则创建
Path(UPLOAD_DIRECTORY).mkdir(parents=True, exist_ok=True)


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

def get_filename(file_path: str):
    return os.path.basename(file_path)

def get_file_title(file_name: str):
    return os.path.splitext(file_name)[0]


@router.post("/", summary='上传文件', dependencies=[DependsJwtAuth])
async def upload_file(file: UploadFile = File(...)):
    filename = file.filename
    resp = {"filename": file.filename}
    if is_excel_file(filename):
        log.info("read excel")
        await read_excel(file)
        return response_base.success(data=resp)
    
    if is_csv_file(filename):
        log.info("read csv")
        await read_text(file)
        return response_base.success(data=resp)
    
    if is_picture_file(filename):
        log.info("read picture")
        await read_picture(file)
        return response_base.success(data=resp)

    if is_media_file(filename):
        log.info("read media")
        await read_media(file)
        return response_base.success(data=resp)

    if is_text_file(filename):
        log.info("read text")
        await read_text(file)
        return response_base.success(data=resp)

    if is_email_file(filename):
        log.info("read email")
        await read_email(file)
        return response_base.success(data=resp)

    if is_pdf_file(filename):
        log.info("read pdf")
        await read_pdf(file)
        return response_base.success(data=resp)
    
    if is_zip_file(filename):
        log.info("read zip")
        await read_zip(file)
        return response_base.success(data=resp)

    log.info("no match, read text")
    await read_text(file)
    return response_base.success(data=resp)



async def read_text(file: UploadFile = File(...)):
    file_location, content = await save_file(file)
    name = get_filename(file.filename)
    title = get_file_title(name)
    content_str = content.decode('utf-8')
    obj: CreateSysDocParam = CreateSysDocParam(title=title, name=name, type="text",content=content_str,
                                                file=file_location)
    await sys_doc_service.create(obj=obj)



async def read_picture(file: UploadFile):
    file_location, _ = await save_file(file)
    name = get_filename(file.filename)
    title = get_file_title(name)
    loop = asyncio.get_running_loop()
    path = f"~/{file_location}"
    pdf_records = await loop.run_in_executor(None, post_imagesocr_recog, path, "~/uploads/result/", "zhen_light")
    content = ''
    if pdf_records:
        content = pdf_records['content']
    obj: CreateSysDocParam = CreateSysDocParam(title=title, name=name, type="picture",content=content,
                                                file=file_location)
    await sys_doc_service.create(obj=obj)

async def read_media(file: UploadFile):
    file_location, _ = await save_file(file)
    name = get_filename(file.filename)
    title = get_file_title(name)
    loop = asyncio.get_running_loop()
    path = f"~/{file_location}"
    pdf_records = await loop.run_in_executor(None, post_audios_recog, path, "~/uploads/result/", "zhen")
    content = ''
    if pdf_records:
        content = pdf_records['content']
    obj: CreateSysDocParam = CreateSysDocParam(title=title, name=name, type="media",content=content,
                                                file=file_location)
    await sys_doc_service.create(obj=obj)


async def read_email(file: UploadFile):
    file_location, _ = await save_file(file)
    name = get_filename(file.filename)
    title = get_file_title(name)
    loop = asyncio.get_running_loop()
    path = f"~/{file_location}"
    pdf_records = await loop.run_in_executor(None, post_emails_recog, path, "~/uploads/附录下载目录/", "~/uploads/附录二次识别输出目录", "zhen_light", "zhen")
    content = ''
    log.info("email res", pdf_records)
    email_subject, email_from, email_to, email_time = '', '', '', ''
    if pdf_records:
        for record in pdf_records:
            co = record["content"]
            if isinstance(co, str):
                content += co
            if isinstance(co, dict):
                email_subject = co["subject"]
                email_from = co["from"]
                email_to = co["to"]
                email_time = co["date"]
    obj: CreateSysDocParam = CreateSysDocParam(title=title, name=name, type="email",content=content,
                                               email_subject=email_subject,email_from=email_from,
                                               email_to=email_to, email_time=email_time, file=file_location)
    await sys_doc_service.create(obj=obj)


async def read_pdf(file: UploadFile = File(...)):
    file_location, _ = await save_file(file)
    name = get_filename(file.filename)
    title = get_file_title(name)
    
    path = f"~/{file_location}"
    loop = asyncio.get_running_loop()
    pdf_records = await loop.run_in_executor(None, post_pdf_recog, path, "~/uploads/result/", "zhen_light")
    content = ''
    if pdf_records:
        content = pdf_records['content']
    obj: CreateSysDocParam = CreateSysDocParam(title=title, name=name, type="pdf",content=content,
                                                file=file_location)
    await sys_doc_service.create(obj=obj)



async def read_excel(file: UploadFile = File(...)):
    # 读取 Excel 文件并解析为 DataFrame
    try:
        df = pd.read_excel(file.file)
    except Exception as e:
        raise e

    # 替换 NaN 为 None（可以避免 PostgreSQL 插入错误）
    df = df.where(pd.notnull(df), None)
    df.replace([np.nan, np.inf, -np.inf], None, inplace=True)

    # 将 DataFrame 转换为 JSON 格式
    data_json = df.to_dict(orient="records")

    # 构建文件保存路径
    file_location, _ = await save_file(file)

    # 将数据存入数据库
    name = get_filename(file.filename)
    title = get_file_title(name)
    content = ''
    for excel_data in data_json:
        strings = dict_to_string(excel_data)
        row = strings + '\n'
        content += row
    content = content.replace("Unnamed", "").replace("None", "")
    doc_param = CreateSysDocParam(title=title, name=name, type='excel', 
                                  c_token=content, content=content, file=file_location)
    doc = await sys_doc_service.create(obj=doc_param)

    for excel_data in data_json:
        param = CreateSysDocDataParam(doc_id=doc.id, excel_data=excel_data)
        await sys_doc_service.create_doc_data(obj=param)
    return response_base.success(data=doc.id)


def dict_to_string(input_dict):
    return ' '.join(f"{key} {value}" for key, value in input_dict.items())

async def save_file(file: UploadFile = File(...)):
    # 构建文件保存路径
    file_location = os.path.join(UPLOAD_DIRECTORY, file.filename)

    # 提取目录部分并创建目录（如果不存在）
    directory = os.path.dirname(file_location)
    os.makedirs(directory, exist_ok=True)

    # 将上传的文件保存到指定目录
    with open(file_location, "wb") as f:
        content = await file.read()
        f.write(content)
    
    return file_location, content



async def read_zip(file: UploadFile = File(...)):
    file_location, _ = await save_file(file)
    with zipfile.ZipFile(file_location, "r") as zip_ref:
        name_list = zip_ref.namelist()
        for file_name in name_list:
            with zip_ref.open(file_name) as single_file:
                try:
                    name = os.path.basename(file_name)
                    title = get_file_title(name)
                    log.info(f"Start read {title}")
                    file_content = single_file.read()
                    # 创建BytesIO对象，模拟上传文件
                    file_bytes = BytesIO(file_content)
                    file_upload_file = UploadFile(
                            file_bytes,
                            filename=file_name,
                    )
                    if is_pdf_file(name):
                        await read_pdf(file_upload_file)
                    if is_excel_file(name):
                        await read_excel(file_upload_file)
                    if is_csv_file(name):
                        await read_text(file)
                    if is_picture_file(name):
                        await read_picture(file_upload_file)
                    if is_media_file(name):
                        await read_media(file_upload_file)
                    if is_text_file(name):
                        await read_text(file_upload_file)
                    if is_email_file(name):
                        await read_email(file_upload_file)
                    log.info(f"Success read {title}")
                except Exception as e:
                    traceback.print_exc()
        os.remove(file_location)
