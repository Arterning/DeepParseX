
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import chardet
import uuid

from backend.app.admin.schema.doc import CreateSysDocParam
from backend.app.admin.schema.doc_data import CreateSysDocDataParam
from backend.app.admin.schema.doc_chunk import CreateSysDocChunkParam
from backend.app.admin.schema.doc_embdding import CreateSysDocEmbeddingParam
from backend.app.admin.service.doc_service import sys_doc_service
from backend.utils.doc_utils import request_process_allkinds_filepath,get_llm_abstract, request_text_to_vector

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
import os
from email import policy
from email.parser import BytesParser
from zipfile import ZipFile
from bs4 import BeautifulSoup
from backend.app.admin.model import SysDoc


# 定义上传文件保存的目录
UPLOAD_DIRECTORY = "uploads"

# 创建上传文件的目录，如果不存在则创建
Path(UPLOAD_DIRECTORY).mkdir(parents=True, exist_ok=True)


class UploadService:

    @staticmethod
    def get_filename(file_path: str):
        return os.path.basename(file_path)
    
    @staticmethod
    def get_file_title(file_name: str):
        return os.path.splitext(file_name)[0]

    @staticmethod
    def get_abs_path(location: str):
        is_in_container = os.path.isdir('/fba/backend')
        if (is_in_container):
            return f"~/{location}"
        absolute_path = os.path.abspath(location)
        return absolute_path

    @staticmethod
    async def read_text(file: UploadFile = File(...)):
        file_location, content ,unique_id= await upload_service.save_file(file)
        name = upload_service.get_filename(file.filename)
        title = upload_service.get_file_title(name)
        loop = asyncio.get_running_loop()
        path = upload_service.get_abs_path(location=file_location)
        content_str = upload_service.decode_content_with_chardet(content)
        pdf_records = await loop.run_in_executor(None, request_process_allkinds_filepath, path)
        desc = ''
        if pdf_records:
            desc = pdf_records['abstract']
        obj: CreateSysDocParam = CreateSysDocParam(title=title, name=name, type="text",content=content_str,
                                                    file=file_location,desc=desc,uuid=unique_id)
        
        doc = await sys_doc_service.create(obj=obj)

        await upload_service.insert_text_embs(doc)

    @staticmethod
    async def insert_text_embs(doc: SysDoc):
        doc_id = doc.id
        doc_name = doc.name
        loop = asyncio.get_running_loop()
        desc_vector = await loop.run_in_executor(None,request_text_to_vector,doc.desc)
        obj_list=[]
        for vector in desc_vector:
            desc_text = vector['text']
            desc_embedding = vector['embs']
            obj = CreateSysDocEmbeddingParam(
                doc_id=doc_id,
                doc_name=doc_name,
                desc=desc_text,
                embedding=desc_embedding
            )
            obj_list.append(obj)
        await sys_doc_service.create_doc_bulk_embedding(obj_list=obj_list)
        

        #所有文本的向量
        vector_data = await loop.run_in_executor(None,request_text_to_vector,doc.content)
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
    async def read_picture(file: UploadFile):
        file_location, _ ,unique_id= await upload_service.save_file(file)
        name = upload_service.get_filename(file.filename)
        title = upload_service.get_file_title(name)
        loop = asyncio.get_running_loop()
        path = upload_service.get_abs_path(location=file_location)
        pdf_records = await loop.run_in_executor(None, request_process_allkinds_filepath, path)
        content = ''
        desc = ''
        if pdf_records:
            content = pdf_records['content']
            desc = pdf_records['abstract']
        
        obj: CreateSysDocParam = CreateSysDocParam(title=title, name=name, type="picture",content=content,
                                                    file=file_location, desc=desc,uuid=unique_id)
        doc = await sys_doc_service.create(obj=obj)

        await upload_service.insert_text_embs(doc)


    @staticmethod
    async def read_media(file: UploadFile):
        file_location, _ ,unique_id= await upload_service.save_file(file)
        name = upload_service.get_filename(file.filename)
        title = upload_service.get_file_title(name)
        loop = asyncio.get_running_loop()
        path = upload_service.get_abs_path(location=file_location)
        pdf_records = await loop.run_in_executor(None, request_process_allkinds_filepath, path)
        content = ''
        desc = ''
        if pdf_records:
            content = pdf_records['content']
            desc = pdf_records['abstract']
        desc_vector = await loop.run_in_executor(None,request_text_to_vector,desc)

        obj: CreateSysDocParam = CreateSysDocParam(title=title, name=name, type="media",content=content,
                                                    file=file_location,desc=desc,uuid=unique_id)
        doc = await sys_doc_service.create(obj=obj)
        await upload_service.insert_text_embs(doc)


    @staticmethod
    async def read_email(file: UploadFile):
        file_location, _ ,unique_id= await upload_service.save_file(file)
        name = upload_service.get_filename(file.filename)
        title = upload_service.get_file_title(name)
        loop = asyncio.get_running_loop()
        path = upload_service.get_abs_path(location=file_location)
        pdf_records = await loop.run_in_executor(None, request_process_allkinds_filepath, path)
        content = ''
        desc = ''
        email_subject, email_from, email_to, email_time = '', '', '', ''
        if pdf_records:
            
            content = pdf_records['content']
            email_subject = content['subject']
            email_from = content['from']
            email_to = content['to']
            email_time = content['date']
            email_body = content['body']
            desc = pdf_records['abstract']
        desc_vector = await loop.run_in_executor(None,request_text_to_vector,desc)
        obj: CreateSysDocParam = CreateSysDocParam(title=title, name=name, type="email",content=email_body,
                                                email_subject=email_subject,email_from=email_from,
                                                email_to=email_to, email_time=email_time, file=file_location,desc=desc,uuid=unique_id)
        doc = await sys_doc_service.create(obj=obj)
        # 获取邮件的id
        doc_id = doc.id
        # 获取附件，下载附件
        await upload_service.emailfile_attachments_downloads(eml_file=file_location , download_folder="uploads",belong=doc_id)



    @staticmethod
    async def read_pdf(file: UploadFile = File(...)):
        file_location, _ ,unique_id= await upload_service.save_file(file)
        name = upload_service.get_filename(file.filename)
        title = upload_service.get_file_title(name)
        path = upload_service.get_abs_path(location=file_location)
        loop = asyncio.get_running_loop()
        pdf_records = await loop.run_in_executor(None, request_process_allkinds_filepath, path)
        content = ''
        desc = ''
        if pdf_records:
            content = pdf_records['content']
            desc = pdf_records['abstract']
    
        obj: CreateSysDocParam = CreateSysDocParam(title=title, name=name, type="pdf",content=content,
                                                    file=file_location,desc=desc,uuid=unique_id)
        doc = await sys_doc_service.create(obj=obj)
        await upload_service.insert_text_embs(doc)


    @staticmethod
    async def read_excel(file: UploadFile = File(...)):
        # 读取 Excel 文件并解析为 DataFrame
        file_content = await file.read()
        file_bytes = BytesIO(file_content)
        try:
            df = pd.read_excel(file_bytes, nrows=10, header=None)
        except Exception as e:
            raise e

        head = 0
        for i, row in df.iterrows():
            if not row.isna().any():
                head = i
                break
        df = pd.read_excel(file_bytes, header=head)

        # 替换 NaN 为 None（可以避免 PostgreSQL 插入错误）
        df = df.where(pd.notnull(df), None)
        df.replace([np.nan, np.inf, -np.inf], None, inplace=True)

        # 将 DataFrame 转换为 JSON 格式
        data_json = df.to_dict(orient="records")
        # 构建文件保存路径
        file_location, _ ,unique_id= await upload_service.save_file(file)

        # 将数据存入数据库
        name = upload_service.get_filename(file.filename)
        title = upload_service.get_file_title(name)
        desc = ''
        content = ''

        loop = asyncio.get_running_loop()
        data_input = df.head(5).to_string(index=False, header=True)
        excel_records = await loop.run_in_executor(None, get_llm_abstract, data_input)
        if excel_records:
            desc = excel_records
            
        
        for excel_data in data_json:
            print("excel_data",excel_data)
            strings = upload_service.dict_to_string(excel_data)
            row = strings + '\n'
            content += row
        content = content.replace("Unnamed", "").replace("None", "")
        doc_param = CreateSysDocParam(title=title, name=name, type='excel', 
                                    c_token=content, content=content, file=file_location,desc=desc,uuid=unique_id)
        doc = await sys_doc_service.create(obj=doc_param)
        doc_id = doc.id
        obj_list = []
        for excel_data in data_json:
            param = CreateSysDocDataParam(doc_id=doc_id, excel_data=excel_data)
            obj_list.append(param)
        await sys_doc_service.create_doc_data(obj_list=obj_list)
        
        await upload_service.insert_text_embs(doc)

    @staticmethod
    def dict_to_string(input_dict: dict) -> str:
        return ' '.join(f"{key} {value}" for key, value in input_dict.items())

    @staticmethod
    async def save_file(file: UploadFile = File(...)):
        unique_id = str(uuid.uuid4())
        # 文件后缀
        file_extension = os.path.splitext(file.filename)[1]
        new_filename = f"{unique_id}{file_extension}"
        print(new_filename)
        # 构建文件保存路径
        file_location = os.path.join(UPLOAD_DIRECTORY, new_filename)
        # 提取目录部分并创建目录（如果不存在）
        directory = os.path.dirname(file_location)
        os.makedirs(directory, exist_ok=True)

        # 将上传的文件保存到指定目录
        with open(file_location, "wb") as f:
            content = await file.read()
            f.write(content)
        
        return file_location, content,unique_id



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
        file_location, _ ,unique_id= await upload_service.save_file(file)
        with upload_service.support_gbk(ZipFile(file_location, "r")) as zip_ref:
            name_list = zip_ref.namelist()
            for file_name in name_list:
                with zip_ref.open(file_name) as single_file:
                    try:
                        name = os.path.basename(file_name)
                        title = upload_service.get_file_title(name)
                        log.info(f"Start read {title}")
                        file_content = single_file.read()
                        # 创建BytesIO对象，模拟上传文件
                        file_bytes = BytesIO(file_content)
                        file_upload_file = UploadFile(
                                file_bytes,
                                filename=file_name,
                        )
                        if upload_service.is_pdf_file(name):
                            await upload_service.read_pdf(file_upload_file)
                        if upload_service.is_excel_file(name):
                            await upload_service.read_excel(file_upload_file)
                        if upload_service.is_csv_file(name):
                            await upload_service.read_text(file)
                        if upload_service.is_picture_file(name):
                            await upload_service.read_picture(file_upload_file)
                        if upload_service.is_media_file(name):
                            await upload_service.read_media(file_upload_file)
                        if upload_service.is_text_file(name):
                            await upload_service.read_text(file_upload_file)
                        if upload_service.is_email_file(name):
                            await upload_service.read_email(file_upload_file)
                        log.info(f"Success read {title}")
                    except Exception as e:
                        traceback.print_exc()
            os.remove(file_location)





    # 3.1 获取邮件正文
    def get_email_body(msg):
        """提取邮件正文，支持纯文本和HTML格式，并从HTML中提取纯文本。"""
        body = {'plain': '', 'html': ''}
        if msg.is_multipart():
            for part in msg.iter_parts():
                content_type = part.get_content_type()
                charset = part.get_content_charset() or 'utf-8'
                if content_type == 'text/plain':
                    body['plain'] += part.get_payload(decode=True).decode(charset)
                elif content_type == 'text/html':
                    # 提取HTML并转换为纯文本
                    html_content = part.get_payload(decode=True).decode(charset)
                    soup = BeautifulSoup(html_content, 'html.parser')
                    body['html'] += soup.get_text()  # 从HTML提取纯文本
        else:
            # 非 multipart 邮件
            content_type = msg.get_content_type()
            charset = msg.get_content_charset() or 'utf-8'
            if content_type == 'text/plain':
                body['plain'] = msg.get_payload(decode=True).decode(charset)
            elif content_type == 'text/html':
                # 提取HTML并转换为纯文本
                html_content = msg.get_payload(decode=True).decode(charset)
                soup = BeautifulSoup(html_content, 'html.parser')
                body['html'] = soup.get_text()  # 从HTML提取纯文本
        return body



    # 3.2 保存附件并记录路径
    async def save_attachments(msg, download_folder, belong):
        """保存附件并返回附件文件路径的列表。"""
        attachments = []
        for part in msg.iter_attachments():
            filename = part.get_filename()
            file_extension = os.path.splitext(filename)[1]
            unique_id = str(uuid.uuid4())
            new_filename = f"{unique_id}{file_extension}"
            if filename:
                file_path = os.path.join(download_folder, new_filename)
                with open(file_path, 'wb') as f:
                    f.write(part.get_payload(decode=True))

                title = upload_service.get_file_title(filename)
                path = upload_service.get_abs_path(location=file_path)
                loop = asyncio.get_running_loop()
                records = await loop.run_in_executor(
                    None, request_process_allkinds_filepath, path
                )
                content = ''
                desc = ''
                if records:
                    if 'content' not in records:
                        log.warning(f"{filename}没有content或者不能处理，跳过")
                        continue
                    content = records['content']
                    desc = records['abstract']
                file_type = upload_service.get_file_type(filename)
                obj: CreateSysDocParam = CreateSysDocParam(
                    title=title,
                    name=filename,
                    type=file_type,
                    content=content,
                    file=file_path,
                    desc=desc,
                    belong=belong,
                    uuid=unique_id
                )
                doc = await sys_doc_service.create(obj=obj)
                await upload_service.insert_text_embs(doc)
                attachments.append(file_path)
        return attachments




    # 3.3 单个邮件附件下载到指定目录，并处理其中所有附件。连同邮件正文一起组合
    async def  emailfile_attachments_downloads( eml_file, download_folder,belong):
        """
        解析 .eml 文件，提取邮件头、正文、附件，并将结果存储为字典。
        附件会保存到指定的文件夹。
        
        参数:
            eml_file (str): .eml 文件的路径
            download_folder (str): 保存附件的文件夹路径 (默认为 "attachments")
        
        返回:
            list[dict]: 邮件内容 + 邮件附件内容
        """
        download_folder = Path(download_folder)
        # 确保保存附件的文件夹存在
        if not os.path.exists(download_folder):
            
            download_folder.mkdir(exist_ok=True,parents=True)

        
        # 读取并解析 .eml 文件
        with open(eml_file, 'rb') as f:
            msg = BytesParser(policy=policy.default).parse(f)

        # 存储邮件信息的字典
        email_data = {
            
        }

        # 获取邮件头信息
        email_data['subject'] = msg['subject']
        email_data['from'] = msg['from']
        email_data['to'] = msg['to']
        email_data['cc'] = msg['cc']
        email_data['bcc'] = msg['bcc']
        email_data['date'] = msg['date']
        email_data['message-id'] = msg['message-id']
        
        
        body_content = upload_service.get_email_body(msg)
        body_content = body_content["plain"] + body_content["html"] ## 合并文本类型数据和html数据
        email_data["body"] = body_content
        # 下载附件
        email_data['attachments'] = await upload_service.save_attachments(msg, download_folder,belong) 


    @staticmethod
    def process_vector_data(vector_data: str) -> list[float]:
        """处理向量数据,将JSON字符串转换为向量数组"""
        try:
            vector_list = json.loads(vector_data)
            all_embeddings = []
            for item in vector_list:
                if "embs" in item:
                    # 直接使用embs数组,不需要extend
                    all_embeddings = item["embs"]
                    break  # 只取第一个文本块的向量
            return all_embeddings
        except Exception as e:
            log.error(f"处理向量数据失败: {str(e)}")
            return None


    

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


upload_service = UploadService()