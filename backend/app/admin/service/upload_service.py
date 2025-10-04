
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
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
import rarfile
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
    is_zip_file,
    is_rar_file,
    is_parquet_file
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

        log.info(f"encoding: {encoding}")
        
        try:
            content_str = content.decode(encoding)
        except (UnicodeDecodeError, TypeError) as e:
            log.error(f"解码失败，尝试使用UTF-8")
            content_str = content.decode('UTF-8', errors='ignore')
        
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
        if not response or 'content' not in response:
            return '无法获取文件解析结果'
        raw_content = response.get('content', '')
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

        if is_zip_file(doc.file_suffix):
            zip_buffer = io.BytesIO(file_bytes)
            with zipfile.ZipFile(zip_buffer, 'r') as zip_ref:
                for file_info in zip_ref.infolist():
                    if file_info.is_dir():
                        continue

                    try:
                        filename = file_info.filename.encode('cp437').decode('gbk')
                    except Exception:
                        filename = file_info.filename
                    
                    if not filename or filename.startswith('__MACOSX'):
                        continue

                    file_content_bytes = zip_ref.read(file_info.filename)

                    unique_id = str(uuid.uuid4())
                    file_suffix = get_file_suffix(filename)
                    new_filename_minio = f"{unique_id}{file_suffix}"

                    file_stream = io.BytesIO(file_content_bytes)
                    object_size = len(file_stream.getbuffer())
                    
                    import mimetypes
                    content_type, _ = mimetypes.guess_type(filename)
                    if content_type is None:
                        content_type = 'application/octet-stream'

                    minio_client.put_object(bucket_name, new_filename_minio, file_stream, object_size, content_type)

                    file_type = get_file_type(file_suffix)

                    obj = CreateSysDocParam(
                        title=filename, 
                        name=filename, 
                        type=file_type,
                        file=new_filename_minio, 
                        uuid=unique_id, 
                        file_suffix=file_suffix,
                        doc_time=datetime(*file_info.date_time) if file_info.date_time else None,
                        size=file_info.file_size,
                        status=0,
                        belong=doc.id,
                        dept_id=doc.dept_id,
                        created_by=doc.created_by,
                        created_user=doc.created_user,
                    )
                    
                    new_doc = await sys_doc_service.create(obj=obj)
                    
                    # Process content for the new doc
                    await upload_service.read_file_content(new_doc)
            
            # Update the zip file doc itself
            content = f"这是一个压缩包，包含 {len(zip_ref.infolist())} 个文件。"
            obj_dict = {
                'content': content,
                'status': 1, # Processed
            }
            await sys_doc_service.base_update(pk=doc.id, obj=obj_dict)
            return

        if is_rar_file(doc.file_suffix):
            rar_buffer = io.BytesIO(file_bytes)
            with rarfile.RarFile(rar_buffer, 'r') as rar_ref:
                for file_info in rar_ref.infolist():
                    if file_info.is_dir():
                        continue

                    try:
                        filename = file_info.filename.encode('cp437').decode('gbk')
                    except Exception:
                        filename = file_info.filename
                    
                    if not filename or filename.startswith('__MACOSX'):
                        continue

                    try:
                        file_content_bytes = rar_ref.read(file_info.filename)
                    except rarfile.BadRarFile as e:
                        log.error(f"Failed to read file {filename} from RAR archive: {e}")
                        continue  # 跳过当前文件，继续处理下一个文件

                    unique_id = str(uuid.uuid4())
                    file_suffix = get_file_suffix(filename)
                    new_filename_minio = f"{unique_id}{file_suffix}"

                    file_stream = io.BytesIO(file_content_bytes)
                    object_size = len(file_stream.getbuffer())
                    
                    import mimetypes
                    content_type, _ = mimetypes.guess_type(filename)
                    if content_type is None:
                        content_type = 'application/octet-stream'

                    minio_client.put_object(bucket_name, new_filename_minio, file_stream, object_size, content_type)

                    file_type = get_file_type(file_suffix)

                    obj = CreateSysDocParam(
                        title=filename, 
                        name=filename, 
                        type=file_type,
                        file=new_filename_minio, 
                        uuid=unique_id, 
                        file_suffix=file_suffix,
                        doc_time=datetime(*file_info.date_time) if file_info.date_time else None,
                        size=file_info.file_size,
                        status=0,
                        belong=doc.id,
                        dept_id=doc.dept_id,
                        created_by=doc.created_by,
                        created_user=doc.created_user,
                    )
                    
                    new_doc = await sys_doc_service.create(obj=obj)
                    
                    # Process content for the new doc
                    await upload_service.read_file_content(new_doc)
            
            # Update the rar file doc itself
            content = f"这是一个压缩包，包含 {len(rar_ref.infolist())} 个文件。"
            obj_dict = {
                'content': content,
                'status': 1, # Processed
            }
            await sys_doc_service.base_update(pk=doc.id, obj=obj_dict)
            return

        if is_text_file(doc.file_suffix):
            content = upload_service.decode_content_with_chardet(file_bytes)

        if is_excel_file(doc.file_suffix):
            content = await upload_service.read_excel_data(doc=doc, file_bytes=file_bytes)
        
        if is_parquet_file(doc.file_suffix):
            content = await upload_service.read_parquet_data(doc=doc, file_bytes=file_bytes)
        
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

        # 其他文件方式的兜底方案
        if content == '':
            content = upload_service.decode_content_with_chardet(file_bytes)


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
            result_dict = await upload_service.do_read_email(doc, file_bytes)
            result_dict["doc_id"] = doc.id
            result_dict["doc_name"] = doc.name
            result_dict["doc_dir_id"] = doc.doc_dir_id
            email_body = await upload_service.save_email(result_dict=result_dict)
            return email_body
        except Exception as e:
            print(f"读取邮件时发生错误：{e}")
            traceback.print_exc()

    @staticmethod
    def extract_email_address(email_string: str) -> tuple[str, str]:
        """
        从 "名称 <邮箱地址>" 格式中提取名称和邮箱地址
        返回元组(名称, 邮箱地址)
        """
        if not email_string:
            return (email_string.strip(), email_string.strip())

        import re
        # 使用正则表达式提取名称和邮箱地址
        match = re.search(r'"?([^"]+)"?\s*<([^<>]+)>', email_string)
        if match:
            name = match.group(1).strip()
            email = match.group(2).strip()
            return (name, email)
        else:
            # 如果没有尖括号，返回去除首尾空格的原字符串作为名称和地址
            return (email_string.strip(), email_string.strip())

    @staticmethod
    def extract_multiple_emails_with_names(email_string: str) -> list[tuple[str, str]]:
        """
        处理多个邮箱地址（逗号分隔），提取每个邮箱的名称和地址
        返回列表[(名称, 邮箱地址), ...]
        """
        if not email_string:
            return []

        import re
        # 使用正则表达式匹配完整的邮箱地址格式
        # 匹配: "名称" <邮箱地址> 或 名称 <邮箱地址> 或 邮箱地址
        email_pattern = r'(?:"([^"]+)"|([^<,]+?))?\s*<([^<>]+)>|([^,<]+@[^,<]+)'
        matches = re.finditer(email_pattern, email_string)
        
        result = []
        for match in matches:
            if match.group(1):  # 匹配到了带引号的名称
                name = match.group(1).strip()
                email = match.group(3).strip()
                result.append((name, email))
            elif match.group(2):  # 匹配到了不带引号的名称
                name = match.group(2).strip()
                email = match.group(3).strip()
                result.append((name, email))
            elif match.group(4):  # 直接匹配到了邮箱地址
                email = match.group(4).strip()
                result.append((email, email))

        return result

    @staticmethod
    def extract_multiple_emails(email_string: str) -> str:
        """
        处理多个邮箱地址（逗号分隔），提取每个邮箱的真实地址
        返回逗号分隔的邮箱地址字符串
        """
        if not email_string:
            return email_string

        import re
        # 使用正则表达式匹配完整的邮箱地址格式
        # 匹配: "名称" <邮箱地址> 或 名称 <邮箱地址> 或 邮箱地址
        email_pattern = r'(?:"[^"]+"|\w[^<,]+?)?\s*<([^<>]+)>|([^,<]+@[^,<]+)'
        matches = re.finditer(email_pattern, email_string)
        
        extracted_emails = []
        for match in matches:
            # 如果匹配到了尖括号中的邮箱地址，取第一个捕获组
            if match.group(1):
                extracted_emails.append(match.group(1).strip())
            # 否则取第二个捕获组（直接的邮箱地址）
            elif match.group(2):
                extracted_emails.append(match.group(2).strip())

        return ', '.join(extracted_emails)

    @staticmethod
    def extract_country(email_address: str) -> str:
        """
        从邮箱地址中推断所属的国家
        根据邮箱域名的顶级域名或特定域名后缀判断国家
        """
        if not email_address or '@' not in email_address:
            return "未知"
        
        # 提取域名部分
        domain = email_address.split('@')[-1].lower()
        
        # 常见国家域名后缀映射表
        country_map = {
            # 亚洲
            '.cn': '中国',
            '.jp': '日本',
            '.kr': '韩国',
            '.sg': '新加坡',
            '.hk': '中国香港',
            '.tw': '中国台湾',
            '.th': '泰国',
            '.my': '马来西亚',
            '.id': '印度尼西亚',
            '.in': '印度',
            '.pk': '巴基斯坦',
            '.bd': '孟加拉国',
            # 欧洲
            '.uk': '英国',
            '.fr': '法国',
            '.de': '德国',
            '.it': '意大利',
            '.es': '西班牙',
            '.ru': '俄罗斯',
            '.pl': '波兰',
            '.gr': '希腊',
            '.nl': '荷兰',
            '.se': '瑞典',
            '.no': '挪威',
            '.dk': '丹麦',
            '.ch': '瑞士',
            '.at': '奥地利',
            # 北美
            '.us': '美国',
            '.ca': '加拿大',
            # 南美
            '.br': '巴西',
            '.ar': '阿根廷',
            '.mx': '墨西哥',
            # 大洋洲
            '.au': '澳大利亚',
            '.nz': '新西兰',
            # 非洲
            '.za': '南非',
            '.ng': '尼日利亚',
        }
        
        # 常见的国际邮箱服务商
        international_domains = {
            'gmail.com': '美国',
            'outlook.com': '美国',
            'hotmail.com': '美国',
            'yahoo.com': '美国',
            'icloud.com': '美国',
            'mail.ru': '俄罗斯',
            'yandex.ru': '俄罗斯',
            'qq.com': '中国',
            '163.com': '中国',
            '126.com': '中国',
            'sina.com': '中国',
            'sohu.com': '中国',
            'aliyun.com': '中国',
            'tencent.com': '中国',
        }
        
        # 优先检查完整域名是否匹配常见服务商
        if domain in international_domains:
            return international_domains[domain]
        
        # 检查顶级域名是否匹配国家
        for tld, country in country_map.items():
            if domain.endswith(tld):
                return country
        
        # 如果以上都不匹配，返回"国际"
        return "国际"

    @staticmethod
    async def save_email(result_dict :dict):
        doc_id = result_dict.get("doc_id")
        doc_name = result_dict.get("doc_name", "")
        doc_dir_id = result_dict.get("doc_dir_id")
        subject = result_dict.get('subject', '')
        from_email_raw = result_dict.get('from', '')
        to_email_raw = result_dict.get('to', '')
        cc_raw = result_dict.get('cc', '')
        bcc_raw = result_dict.get('bcc', '')
        time = result_dict.get('parsed_date', datetime.now())
        body = result_dict.get('body', '')

        # 提取真正的邮箱地址和名称
        from_name, from_email = upload_service.extract_email_address(from_email_raw)
        # 处理多个收件人邮箱地址和名称
        to_emails_with_names = upload_service.extract_multiple_emails_with_names(to_email_raw)
        cc_emails_with_names = upload_service.extract_multiple_emails_with_names(cc_raw)
        bcc_emails_with_names = upload_service.extract_multiple_emails_with_names(bcc_raw)
        
        # 用于msg_obj的字符串格式邮箱
        to_email = ', '.join([email for _, email in to_emails_with_names])
        cc = ', '.join([email for _, email in cc_emails_with_names])
        bcc = ', '.join([email for _, email in bcc_emails_with_names])

        # 获取附件信息，如果没有则设为空列表
        attachments = result_dict.get('attachments', [])
        
        msg_obj = CreateMailMsgParam(
            doc_id=doc_id,
            doc_name=doc_name,
            doc_dir_id=doc_dir_id,
            name=subject,
            subject=subject,
            original=body,
            from_row=from_email_raw,
            to_row=to_email_raw,
            cc_row=cc_raw,
            bcc_row=bcc_raw,
            sender=from_email,
            receiver=to_email,
            cc=cc,
            bcc=bcc,
            time=time,
            attachments=attachments,
        )
        await mail_msg_service.create(obj=msg_obj)

        # 处理发件人邮箱
        if from_email:
            from_box = await mail_box_service.get_by_name(name=from_email)  # 仍使用email作为唯一标识
            if from_box:
                await mail_box_service.base_update(pk=from_box.id, obj={'email_num': from_box.email_num + 1})
            else:
                country = upload_service.extract_country(from_email)
                from_mail_obj = CreateMailBoxParam(
                    user_name=from_name,  # 使用提取的名称
                    name=from_email,
                    email_num=1,
                    country=country,
                )
                await mail_box_service.create(obj=from_mail_obj)

        # 处理To字段的多个邮箱地址
        for name, email_addr in to_emails_with_names:
            to_box = await mail_box_service.get_by_name(name=email_addr)  # 仍使用email作为唯一标识
            if to_box:
                await mail_box_service.base_update(pk=to_box.id, obj={'email_num': to_box.email_num + 1})
            else:
                country = upload_service.extract_country(email_addr)
                to_mail_obj = CreateMailBoxParam(
                    user_name=name,  # 使用提取的名称
                    name=email_addr,
                    email_num=1,
                    country=country,
                )
                await mail_box_service.create(obj=to_mail_obj)

        # 处理CC字段的多个邮箱地址
        for name, email_addr in cc_emails_with_names:
            cc_box = await mail_box_service.get_by_name(name=email_addr)  # 仍使用email作为唯一标识
            if cc_box:
                await mail_box_service.base_update(pk=cc_box.id, obj={'email_num': cc_box.email_num + 1})
            else:
                country = upload_service.extract_country(email_addr)
                cc_mail_obj = CreateMailBoxParam(
                    user_name=name,  # 使用提取的名称
                    name=email_addr,
                    email_num=1,
                    country=country,
                )
                await mail_box_service.create(obj=cc_mail_obj)

        # 处理Bcc字段的多个邮箱地址
        for name, email_addr in bcc_emails_with_names:
            bcc_box = await mail_box_service.get_by_name(name=email_addr)  # 仍使用email作为唯一标识
            if bcc_box:
                await mail_box_service.base_update(pk=bcc_box.id, obj={'email_num': bcc_box.email_num + 1})
            else:
                country = upload_service.extract_country(email_addr)
                bcc_mail_obj = CreateMailBoxParam(
                    user_name=name,  # 使用提取的名称
                    name=email_addr,
                    email_num=1,
                    country=country,
                )
                await mail_box_service.create(obj=bcc_mail_obj)
        return body


    @staticmethod
    async def do_read_email(doc: SysDoc, file_bytes: bytes):
        
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
                'bcc': msg.get('Bcc', ''),
                'date': msg.get('Date', ''),
                'content_type': msg.get_content_type(),
                'attachments': [],
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
                    content_disposition = str(part.get("Content-Disposition", ""))
                    
                    if "attachment" in content_disposition:
                        filename = part.get_filename()
                        if filename:
                            file_content_bytes = part.get_payload(decode=True)
                            
                            unique_id = str(uuid.uuid4())
                            file_suffix = get_file_suffix(filename)
                            new_filename_minio = f"{unique_id}{file_suffix}"

                            file_stream = io.BytesIO(file_content_bytes)
                            object_size = len(file_stream.getbuffer())
                            
                            import mimetypes
                            content_type_mime, _ = mimetypes.guess_type(filename)
                            if content_type_mime is None:
                                content_type_mime = 'application/octet-stream'

                            minio_client.put_object(bucket_name, new_filename_minio, file_stream, object_size, content_type_mime)

                            file_type = get_file_type(file_suffix)

                            obj = CreateSysDocParam(
                                title=filename, 
                                name=filename, 
                                type=file_type,
                                file=new_filename_minio, 
                                uuid=unique_id, 
                                file_suffix=file_suffix,
                                doc_time=datetime.datetime.now(),
                                size=len(file_content_bytes),
                                status=0,
                                belong=doc.id,
                                dept_id=doc.dept_id,
                                created_by=doc.created_by,
                                created_user=doc.created_user,
                            )
                            
                            new_doc = await sys_doc_service.create(obj=obj)
                            
                            # 将附件信息添加到email_data['attachments']
                            email_data['attachments'].append({
                                'id': new_doc.id,
                                'name': filename
                            })
                            
                            # Process content for the new doc
                            try:
                                await upload_service.read_file_content(new_doc)
                            except Exception as e:
                                print(f"处理附件 {filename} 时发生错误: {e}")
                                traceback.print_exc()
                                continue

                            await sys_doc_service.create_doc_tokens(id=new_doc.id)

                            await sys_doc_service.base_update(pk=new_doc.id, obj={
                                'status': 1,
                            })
                        continue
                    
                    content_type = part.get_content_type()
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
    async def read_parquet_data(doc: SysDoc, file_bytes: bytes):
        import pyarrow.parquet as pq
        from io import BytesIO
        
        # 读取 parquet 文件
        buffer = BytesIO(file_bytes)
        table = pq.read_table(buffer)
        df = table.to_pandas()
        
        # 限制行数以避免内容过大
        if len(df) > 100:
            df_sample = df.head(100)
            content = f"Parquet文件包含 {len(df)} 行，{len(df.columns)} 列。以下是前100行的数据预览：\n\n"
        else:
            df_sample = df
            content = f"Parquet文件包含 {len(df)} 行，{len(df.columns)} 列。完整数据如下：\n\n"
        
        # 添加列信息
        content += "列信息：\n"
        for col in df.columns:
            content += f"- {col}: {str(df[col].dtype)}\n"
        content += "\n"
        
        # 替换 NaN 为 None
        df_sample = df_sample.where(pd.notnull(df_sample), None)
        df_sample.replace([np.nan, np.inf, -np.inf], None, inplace=True)
        
        # 将 DataFrame 转换为字符串格式
        for index, row in df_sample.iterrows():
            row_data = {}
            for col in df_sample.columns:
                row_data[col] = row[col]
            strings = upload_service.dict_to_string(row_data)
            content += strings + '\n'
        
        # 将数据保存到数据库
        doc_id = doc.id
        obj_list = []
        data_json = df_sample.to_dict(orient="records")
        for parquet_data in data_json:
            param = CreateSysDocDataParam(doc_id=doc_id, excel_data=parquet_data)
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



upload_service = UploadService()