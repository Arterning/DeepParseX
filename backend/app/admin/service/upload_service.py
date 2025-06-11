
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import chardet
import uuid

from backend.core.conf import settings
from backend.app.admin.schema.doc import CreateSysDocParam, UpdateSysDocParam
from backend.app.admin.schema.doc_data import CreateSysDocDataParam
from backend.app.admin.schema.doc_chunk import CreateSysDocChunkParam
from backend.app.admin.schema.doc_embdding import CreateSysDocEmbeddingParam
from backend.app.admin.schema.mail_msg import CreateMailMsgParam
from backend.app.admin.schema.mail_box import CreateMailBoxParam
from backend.app.admin.service.doc_service import sys_doc_service
from backend.app.admin.service.mail_msg_service import mail_msg_service
from backend.app.admin.service.mail_box_service import mail_box_service
from backend.utils.doc_utils import process_file, request_text_to_vector

import os
import json
from fastapi import File, UploadFile
from pathlib import Path
import pandas as pd
import numpy as np
import asyncio
from io import BytesIO
from backend.common.log import log
import traceback
import zipfile
import io
import os
from email import policy
from email.parser import BytesParser
from zipfile import ZipFile
from bs4 import BeautifulSoup
from backend.app.admin.model import SysDoc
from backend.utils.oss_client import minio_client
from backend.utils.upload_utils import (
    get_file_suffix, 
    get_file_type, 
    is_text_file, 
    is_picture_file, 
    is_excel_file, 
    is_email_file, 
    is_pdf_file,
    is_docx_file,
    is_pptx_file,
    is_media_file,
    is_zip_file
    )

bucket_name = settings.BUCKET_NAME

class UploadService:

    
    # 提取内容
    @staticmethod
    async def extract_text(*, pk: int):
        # 获取文档
        doc = await sys_doc_service.get(pk=pk)
        bucket_name = settings.BUCKET_NAME
        obj_name = doc.file
        response = minio_client.get_object(bucket_name, obj_name)
        file_bytes = response.read()
        content = await upload_service.request_content(title=doc.title, file_bytes=file_bytes)
        await sys_doc_service.base_update(pk=doc.id, obj={
            "content": content
        })
        return content


    @staticmethod
    def decode_content_with_chardet(content):
        # 使用 chardet 检测编码
        result = chardet.detect(content)
        encoding = result['encoding']
        
        try:
            content_str = content.decode(encoding)
        except (UnicodeDecodeError, TypeError) as e:
            print(f"解码失败，尝试使用检测到的编码: {encoding}")
            content_str = content.decode(encoding, errors='ignore')
        
        return content_str

    @staticmethod
    def get_filename(file_path: str):
        return os.path.basename(file_path)
    
    @staticmethod
    def get_file_title(file_name: str):
        return os.path.splitext(file_name)[0]


    @staticmethod
    async def save_file(file: UploadFile = File(...), meta: dict = {}, user = None):
        unique_id = str(uuid.uuid4())
        # 文件后缀
        file_suffix = get_file_suffix(file.filename)
        new_filename = f"{unique_id}{file_suffix}"

        file_content = await file.read()
        file_stream = io.BytesIO(file_content)
        object_size = len(file_stream.getbuffer())
        minio_client.put_object(bucket_name, new_filename, file_stream, object_size, file.content_type)


        file_type = get_file_type(file_suffix)
        last_modified = meta.get('last_modified', None)
        size = meta.get('size', None)

        obj = CreateSysDocParam(
            title=file.filename, 
            name=file.filename, 
            type=file_type,
            file=new_filename, 
            uuid=unique_id, 
            file_suffix=file_suffix,
            doc_time=last_modified,
            size=size,
            status=0,
            dept_id= user.dept_id if user else None,
            created_by= user.id if user else None,
            created_user= user.username if user else None,
        )
        
        doc = await sys_doc_service.create(obj=obj)

        return doc

    @staticmethod
    def sanitize_text(text: str) -> str:
        # 移除空字节和其他非法字符
        return text.replace('\x00', '').encode('utf-8', errors='ignore').decode('utf-8')

    @staticmethod
    async def request_content(title, file_bytes: bytes):
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, process_file, title, file_bytes)
        raw_content = response['content']
        clean_content = upload_service.sanitize_text(raw_content)
        return clean_content

    @staticmethod
    async def read_file_content(doc: SysDoc):
        if doc.content:
            return
        
        content = ''
        desc = ''

        response = minio_client.get_object(bucket_name, doc.file)
        file_bytes = response.read()

        if is_text_file(doc.file_suffix):
            content = upload_service.decode_content_with_chardet(file_bytes)

        if is_excel_file(doc.file_suffix):
            content = await upload_service.read_excel_data(doc=doc, file_bytes=file_bytes)
        
        if is_email_file(doc.file_suffix):
            content = await upload_service.read_email_data(doc=doc, file_bytes=file_bytes)

        if is_picture_file(doc.file_suffix):
            content = "图片文件无法直接读取内容，请查看附件。"
            content = await upload_service.request_content(title=doc.title, file_bytes=file_bytes)
        
        
        if is_pdf_file(doc.file_suffix):
            content = "PDF文件无法直接读取内容，请查看附件。"
            content = await upload_service.request_content(title=doc.title, file_bytes=file_bytes)
        
        if is_docx_file(doc.file_suffix) or is_media_file(doc.file_suffix) or is_pptx_file(doc.file_suffix):
            content = await upload_service.request_content(title=doc.title, file_bytes=file_bytes)


        obj_dict = {
            'content': content,
            'desc': desc,
        }
        await sys_doc_service.base_update(pk=doc.id, obj=obj_dict)



    @staticmethod
    async def insert_text_embs(*, id: int):
        doc = await sys_doc_service.get(pk=id)
        doc_id = doc.id
        doc_name = doc.name
        loop = asyncio.get_running_loop()
        # desc_vector = await loop.run_in_executor(None,request_text_to_vector,doc.desc)
        # obj_list=[]
        # for vector in desc_vector:
        #     desc_text = vector['text']
        #     desc_embedding = vector['embs']
        #     obj = CreateSysDocEmbeddingParam(
        #         doc_id=doc_id,
        #         doc_name=doc_name,
        #         desc=desc_text,
        #         embedding=desc_embedding
        #     )
        #     obj_list.append(obj)
        # await sys_doc_service.create_doc_bulk_embedding(obj_list=obj_list)
        if not doc.content:
            return

        #所有文本的向量
        vector_data = await loop.run_in_executor(None, request_text_to_vector, doc.content)
        obj_list=[]
        for vector in vector_data:
            chunk_text = vector['text']
            chunk_embedding = vector['embs']
            obj = CreateSysDocChunkParam(
                doc_id=doc_id,
                doc_name=doc_name,
                chunk_text=chunk_text,
                chunk_embedding=chunk_embedding
            )
            obj_list.append(obj)
        await sys_doc_service.create_doc_bulk_chunks(obj_list=obj_list)

    @staticmethod
    async def read_email_data(doc: SysDoc, file_bytes: bytes):
        if doc.type != '邮件':
            return None
        
        try:
            result_dict = upload_service.do_read_email(file_bytes)
            email_body = await upload_service.save_email(result_dict=result_dict)
            return email_body
        except Exception as e:
            print(f"读取文件时发生错误：{e}")
            raise e

    @staticmethod
    async def save_email(result_dict :dict):
        subject = result_dict.get('subject', '')
        from_email = result_dict.get('from', '')
        to_email = result_dict.get('to', '')
        cc = result_dict.get('cc', '')
        time = result_dict.get('parsed_date', '')
        body = result_dict.get('body', '')
        msg_obj = CreateMailMsgParam(
            name=subject,
            original=body,
            sender=from_email,
            receiver=to_email,
            cc=cc,
            time=time,
        )
        await mail_msg_service.create(obj=msg_obj)

        from_mail_obj = CreateMailBoxParam(
            name=from_email,
        )
        await mail_box_service.create(obj=from_mail_obj)

        to_mail_obj = CreateMailBoxParam(
            name=to_email,
        )
        await mail_box_service.create(obj=to_mail_obj)
        return body


    @staticmethod
    def do_read_email(file_bytes: bytes):
        
        if not file_bytes:
            return None
        
        try:
            import email
            from email.parser import BytesParser
            from email.policy import default
            import datetime
            
            # 解析邮件
            parser = BytesParser(policy=default)
            msg = parser.parsebytes(file_bytes)
            
            # 获取基本信息
            email_data = {
                'subject': msg.get('Subject', ''),
                'from': msg.get('From', ''),
                'to': msg.get('To', ''),
                'cc': msg.get('Cc', ''),
                'date': msg.get('Date', ''),
                'content_type': msg.get_content_type(),
            }
            
            # 处理日期格式
            if email_data['date']:
                try:
                    # 尝试解析邮件日期为datetime对象
                    date_tuple = email.utils.parsedate_tz(email_data['date'])
                    if date_tuple:
                        timestamp = email.utils.mktime_tz(date_tuple)
                        dt = datetime.datetime.fromtimestamp(timestamp)
                        email_data['parsed_date'] = dt
                except Exception as e:
                    print(f"解析日期时发生错误: {e}")
                    email_data['parsed_date'] = None
            
            # 获取邮件正文
            email_data['body'] = ''
            
            # 处理纯文本内容
            plain_text = None
            html_content = None
            
            # 获取邮件内容
            if msg.is_multipart():
                # 多部分邮件
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition", ""))
                    
                    # 跳过附件
                    if "attachment" in content_disposition:
                        continue
                    
                    # 获取正文
                    if content_type == "text/plain" and not plain_text:
                        plain_text = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='replace')
                    elif content_type == "text/html" and not html_content:
                        html_content = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='replace')
            else:
                # 单部分邮件
                content_type = msg.get_content_type()
                if content_type == "text/plain":
                    plain_text = msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', errors='replace')
                elif content_type == "text/html":
                    html_content = msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', errors='replace')
            
            # 优先使用纯文本内容，如果没有则使用HTML内容
            email_data['body'] = plain_text or html_content or ''
            
            # 处理附件
            attachments = []
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_maintype() == 'multipart':
                        continue
                    
                    content_disposition = str(part.get("Content-Disposition", ""))
                    if "attachment" in content_disposition:
                        filename = part.get_filename()
                        if filename:
                            attachments.append({
                                'filename': filename,
                                'content_type': part.get_content_type(),
                                'size': len(part.get_payload(decode=True))
                            })
            
            email_data['attachments'] = attachments
            
            return email_data
        
        except Exception as e:
            print(f"解析邮件时发生错误：{e}")
            raise e
        


    @staticmethod
    async def read_excel_data(doc: SysDoc, file_bytes: bytes):

        # 用 mimetypes 和文件头判断格式
        buffer = BytesIO(file_bytes)
        file_start = buffer.read(8)
        buffer.seek(0)

        # 判断格式：前8字节可识别是 xls 还是 xlsx
        is_xlsx = file_start.startswith(b'PK')  # zip格式，xlsx 本质上是压缩包
        is_xls = file_start[:2] == b'\xD0\xCF'  # ole2格式，xls 特征头

        if is_xlsx:
            engine = "openpyxl"
        elif is_xls:
            engine = "xlrd"
        else:
            raise ValueError("不支持的 Excel 文件格式，请上传 .xls 或 .xlsx 文件")


        # 读取文件内容
        df = pd.read_excel(BytesIO(file_bytes), nrows=10, header=None, engine=engine)
        

        head = 0
        for i, row in df.iterrows():
            if not row.isna().any():
                head = i
                break
        df = pd.read_excel(BytesIO(file_bytes), header=head, engine=engine)

        # 替换 NaN 为 None（可以避免 PostgreSQL 插入错误）
        df = df.where(pd.notnull(df), None)
        df.replace([np.nan, np.inf, -np.inf], None, inplace=True)

        # 将 DataFrame 转换为 JSON 格式
        data_json = df.to_dict(orient="records")

        content = ''
        
        for excel_data in data_json:
            # print("excel_data",excel_data)
            strings = upload_service.dict_to_string(excel_data)
            row = strings + '\n'
            content += row
        content = content.replace("Unnamed", "").replace("None", "")
        doc_id = doc.id
        obj_list = []
        for excel_data in data_json:
            param = CreateSysDocDataParam(doc_id=doc_id, excel_data=excel_data)
            obj_list.append(param)
        await sys_doc_service.create_doc_data(obj_list=obj_list)
        return content
        


    @staticmethod
    def dict_to_string(input_dict: dict) -> str:
        return ' '.join(f"{key} {value}" for key, value in input_dict.items())



    def support_gbk(zip_file: ZipFile):
        name_to_info = zip_file.NameToInfo
        # copy map first
        for name, info in name_to_info.copy().items():
            real_name = name.encode('cp437').decode('gbk')
            if real_name != name:
                info.filename = real_name
                del name_to_info[name]
                name_to_info[real_name] = info
        return zip_file


    @staticmethod
    async def read_zip(file: UploadFile = File(...)):
        doc = await upload_service.save_file(file)
        # file_location = upload_service.get_abs_path(location=doc.file)
        # with upload_service.support_gbk(ZipFile(file_location, "r")) as zip_ref:
        #     name_list = zip_ref.namelist()
        #     for file_name in name_list:
        #         with zip_ref.open(file_name) as single_file:
        #             try:
        #                 log.info(f"Start read {file_name}")
        #                 # 创建BytesIO对象，模拟上传文件
        #                 # file_bytes = BytesIO(file_content)
        #                 # file_upload_file = UploadFile(
        #                 #         file_bytes,
        #                 #         filename=file_name,
        #                 # )
        #                 await sys_doc_service.update_doc_tokens(doc=doc)
        #                 await upload_service.insert_text_embs(doc=doc)
        #                 log.info(f"Success read {file_name}")
        #             except Exception as e:
        #                 traceback.print_exc()
        #     os.remove(file_location)




upload_service = UploadService()