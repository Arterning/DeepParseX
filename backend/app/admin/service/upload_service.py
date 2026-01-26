
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
import chardet
import uuid
import os
import json
from fastapi import File, UploadFile
from pathlib import Path
import pandas as pd
import numpy as np
import asyncio
from functools import partial
from io import BytesIO
import traceback
import zipfile
import io
import os
from zipfile import ZipFile
import rarfile

from backend.core.conf import settings
from backend.common.log import log
from backend.common.context import get_current_user
from backend.app.admin.model import SysDoc
from backend.app.admin.schema.doc import CreateSysDocParam, UpdateSysDocParam
from backend.app.admin.schema.doc_data import CreateSysDocDataParam
from backend.app.admin.schema.mail_msg import CreateMailMsgParam
from backend.app.admin.schema.mail_box import CreateMailBoxParam
from backend.app.admin.service.doc_service import sys_doc_service
from backend.app.admin.service.mail_msg_service import mail_msg_service
from backend.app.admin.service.mail_box_service import mail_box_service
from backend.app.admin.utils.text_processor import process_file, classify_text_tags
from backend.app.admin.utils.spam_detector import spam_detector
from backend.app.admin.service.tag_service import tag_service
from backend.app.admin.utils.tabular_processor import tabular_processor
from backend.app.admin.utils.email_parser import EmailParser
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
    is_zip_file,
    is_rar_file,
    is_parquet_file,
    is_mbox_file,
    is_csv_file
    )

bucket_name = settings.BUCKET_NAME

class UploadService:

    # ============ 异步包装器方法 ============
    @staticmethod
    async def _run_in_thread(func, *args, **kwargs):
        """将同步函数放到线程池中执行，避免阻塞事件循环"""
        if kwargs:
            func = partial(func, **kwargs)
        return await asyncio.to_thread(func, *args)

    @staticmethod
    async def _minio_get_object(bucket_name: str, obj_name: str) -> bytes:
        """异步获取 MinIO 对象"""
        def _sync_get():
            response = minio_client.get_object(bucket_name, obj_name)
            return response.read()
        return await asyncio.to_thread(_sync_get)

    @staticmethod
    async def _minio_put_object(bucket_name: str, obj_name: str, data: bytes, content_type: str):
        """异步上传对象到 MinIO"""
        def _sync_put():
            file_stream = io.BytesIO(data)
            object_size = len(data)
            minio_client.put_object(bucket_name, obj_name, file_stream, object_size, content_type)
        await asyncio.to_thread(_sync_put)

    @staticmethod
    def _extract_zip_files_sync(file_bytes: bytes) -> list[dict]:
        """同步解压 zip 文件，返回文件信息列表"""
        import mimetypes
        extracted_files = []
        zip_buffer = io.BytesIO(file_bytes)
        with zipfile.ZipFile(zip_buffer, 'r') as zip_ref:
            for file_info in zip_ref.infolist():
                if file_info.is_dir():
                    continue
                try:
                    filename = file_info.filename.encode('cp437').decode('gbk')
                except Exception:
                    filename = file_info.filename
                # 清理文件名中的空字节
                if filename:
                    filename = filename.replace('\x00', '').encode('utf-8', errors='ignore').decode('utf-8')
                if not filename or filename.startswith('__MACOSX'):
                    continue
                file_content_bytes = zip_ref.read(file_info.filename)
                unique_id = str(uuid.uuid4())
                file_suffix = get_file_suffix(filename)
                new_filename_minio = f"{unique_id}{file_suffix}"
                content_type, _ = mimetypes.guess_type(filename)
                if content_type is None:
                    content_type = 'application/octet-stream'
                extracted_files.append({
                    'filename': filename,
                    'file_content_bytes': file_content_bytes,
                    'unique_id': unique_id,
                    'file_suffix': file_suffix,
                    'new_filename_minio': new_filename_minio,
                    'content_type': content_type,
                    'file_type': get_file_type(file_suffix),
                    'date_time': file_info.date_time,
                    'file_size': file_info.file_size,
                })
            total_count = len(zip_ref.infolist())
        return extracted_files, total_count

    @staticmethod
    def _extract_rar_files_sync(file_bytes: bytes) -> list[dict]:
        """同步解压 rar 文件，返回文件信息列表"""
        import mimetypes
        extracted_files = []
        rar_buffer = io.BytesIO(file_bytes)
        with rarfile.RarFile(rar_buffer, 'r') as rar_ref:
            for file_info in rar_ref.infolist():
                if file_info.is_dir():
                    continue
                try:
                    filename = file_info.filename.encode('cp437').decode('gbk')
                except Exception:
                    filename = file_info.filename
                # 清理文件名中的空字节
                if filename:
                    filename = filename.replace('\x00', '').encode('utf-8', errors='ignore').decode('utf-8')
                if not filename or filename.startswith('__MACOSX'):
                    continue
                try:
                    file_content_bytes = rar_ref.read(file_info.filename)
                except rarfile.BadRarFile as e:
                    log.error(f"Failed to read file {filename} from RAR archive: {e}")
                    continue
                unique_id = str(uuid.uuid4())
                file_suffix = get_file_suffix(filename)
                new_filename_minio = f"{unique_id}{file_suffix}"
                content_type, _ = mimetypes.guess_type(filename)
                if content_type is None:
                    content_type = 'application/octet-stream'
                extracted_files.append({
                    'filename': filename,
                    'file_content_bytes': file_content_bytes,
                    'unique_id': unique_id,
                    'file_suffix': file_suffix,
                    'new_filename_minio': new_filename_minio,
                    'content_type': content_type,
                    'file_type': get_file_type(file_suffix),
                    'date_time': file_info.date_time,
                    'file_size': file_info.file_size,
                })
            total_count = len(rar_ref.infolist())
        return extracted_files, total_count


    @staticmethod
    def ensure_bucket_exists(bucket_name):
        """确保bucket存在，如果不存在则创建并设置为public权限"""
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
            # 设置bucket为public权限
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": ["s3:GetObject"],
                        "Effect": "Allow",
                        "Principal": {"AWS": ["*"]},
                        "Resource": [f"arn:aws:s3:::{bucket_name}/*"],
                        "Sid": "PublicRead"
                    }
                ]
            }
            minio_client.set_bucket_policy(bucket_name, json.dumps(policy))
            log.info(f"Bucket {bucket_name} created successfully with public access policy")
        return bucket_name
    
    # 提取内容
    @staticmethod
    async def extract_text(*, pk: int):
        # 获取文档
        doc = await sys_doc_service.get(pk=pk)
        bucket_name = settings.BUCKET_NAME
        obj_name = doc.file
        # 确保bucket存在（放到线程池执行）
        await asyncio.to_thread(UploadService.ensure_bucket_exists, bucket_name)
        # 异步获取文件内容
        file_bytes = await UploadService._minio_get_object(bucket_name, obj_name)
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

        # GB2312/GBK/GB18030 兼容性处理：GB18030 > GBK > GB2312
        # 如果检测到 GB2312，优先尝试 GBK 和 GB18030，因为它们是 GB2312 的超集
        gb_encodings = ['gb2312', 'gbk', 'gb18030']
        if encoding and encoding.lower() in gb_encodings:
            # 按兼容性从高到低尝试
            for enc in ['gb18030', 'gbk', 'gb2312']:
                try:
                    content_str = content.decode(enc)
                    log.info(f"使用 {enc} 解码成功")
                    return content_str
                except (UnicodeDecodeError, LookupError):
                    continue

        # 常规解码尝试
        try:
            content_str = content.decode(encoding)
        except (UnicodeDecodeError, TypeError, LookupError) as e:
            log.error(f"使用 {encoding} 解码失败，尝试其他编码")
            # 尝试常见编码
            for fallback_enc in ['utf-8', 'gb18030', 'gbk', 'latin-1']:
                try:
                    content_str = content.decode(fallback_enc)
                    log.info(f"使用 {fallback_enc} 解码成功")
                    return content_str
                except (UnicodeDecodeError, LookupError):
                    continue
            # 最后使用 UTF-8 忽略错误
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
        # 确保bucket存在（放到线程池执行）
        await asyncio.to_thread(UploadService.ensure_bucket_exists, bucket_name)
        # 异步上传到 MinIO
        await UploadService._minio_put_object(bucket_name, new_filename, file_content, file.content_type)


        file_type = get_file_type(file_suffix)
        last_modified = meta.get('last_modified', None)
        size = meta.get('size', None)

        # 如果没有传入 user 参数，则从上下文中获取
        if user is None:
            user = get_current_user()

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
        # 直接await调用异步版本的process_file
        response = await process_file(title, file_bytes)
        if not response or 'content' not in response:
            return ""
        raw_content = response.get('content', '')
        clean_content = upload_service.sanitize_text(raw_content)
        return clean_content

    @staticmethod
    async def read_file_content(doc: SysDoc):
        if doc.content:
            return

        content = ''
        desc = ''

        # 确保bucket存在（放到线程池执行）
        await asyncio.to_thread(UploadService.ensure_bucket_exists, bucket_name)
        # 异步获取文件内容
        file_bytes = await UploadService._minio_get_object(bucket_name, doc.file)

        if is_zip_file(doc.file_suffix):
            # 在线程池中执行同步解压操作
            extracted_files, total_count = await asyncio.to_thread(
                UploadService._extract_zip_files_sync, file_bytes
            )
            # 异步处理每个解压出的文件
            for file_data in extracted_files:
                # 异步上传到 MinIO
                await UploadService._minio_put_object(
                    bucket_name,
                    file_data['new_filename_minio'],
                    file_data['file_content_bytes'],
                    file_data['content_type']
                )
                obj = CreateSysDocParam(
                    title=file_data['filename'],
                    name=file_data['filename'],
                    type=file_data['file_type'],
                    file=file_data['new_filename_minio'],
                    uuid=file_data['unique_id'],
                    file_suffix=file_data['file_suffix'],
                    doc_time=datetime(*file_data['date_time']) if file_data['date_time'] else None,
                    size=file_data['file_size'],
                    status=0,
                    belong=doc.id,
                    doc_dir_id=doc.doc_dir_id,
                    dept_id=doc.dept_id,
                    created_by=doc.created_by,
                    created_user=doc.created_user,
                )
                new_doc = await sys_doc_service.create(obj=obj)

            # Update the zip file doc itself
            content = f"这是一个压缩包，包含 {total_count} 个文件。"
            obj_dict = {
                'content': content,
                'status': 1,  # Processed
            }
            await sys_doc_service.base_update(pk=doc.id, obj=obj_dict)
            return

        if is_rar_file(doc.file_suffix):
            # 在线程池中执行同步解压操作
            extracted_files, total_count = await asyncio.to_thread(
                UploadService._extract_rar_files_sync, file_bytes
            )
            # 异步处理每个解压出的文件
            for file_data in extracted_files:
                # 异步上传到 MinIO
                await UploadService._minio_put_object(
                    bucket_name,
                    file_data['new_filename_minio'],
                    file_data['file_content_bytes'],
                    file_data['content_type']
                )
                obj = CreateSysDocParam(
                    title=file_data['filename'],
                    name=file_data['filename'],
                    type=file_data['file_type'],
                    file=file_data['new_filename_minio'],
                    uuid=file_data['unique_id'],
                    file_suffix=file_data['file_suffix'],
                    doc_time=datetime(*file_data['date_time']) if file_data['date_time'] else None,
                    size=file_data['file_size'],
                    status=0,
                    belong=doc.id,
                    doc_dir_id=doc.doc_dir_id,
                    dept_id=doc.dept_id,
                    created_by=doc.created_by,
                    created_user=doc.created_user,
                )
                new_doc = await sys_doc_service.create(obj=obj)

            # Update the rar file doc itself
            content = f"这是一个压缩包，包含 {total_count} 个文件。"
            obj_dict = {
                'content': content,
                'status': 1,  # Processed
            }
            await sys_doc_service.base_update(pk=doc.id, obj=obj_dict)
            return

        if is_mbox_file(doc.file_suffix):
            try:
                # 在线程池中执行同步的 mbox 解析操作
                extracted_emails = await asyncio.to_thread(
                    EmailParser.extract_mbox_emails_sync, file_bytes
                )
                # 异步处理每封邮件
                for email_data in extracted_emails:
                    # 异步上传到 MinIO
                    await UploadService._minio_put_object(
                        bucket_name,
                        email_data['new_filename_minio'],
                        email_data['email_bytes'],
                        'message/rfc822'
                    )
                    # 创建新的 SysDoc 记录
                    obj = CreateSysDocParam(
                        title=email_data['subject'],
                        name=email_data['subject'],
                        type='邮件',
                        file=email_data['new_filename_minio'],
                        uuid=email_data['unique_id'],
                        file_suffix='.eml',
                        doc_time=datetime.now(),
                        size=len(email_data['email_bytes']),
                        status=0,
                        belong=doc.id,
                        dept_id=doc.dept_id,
                        created_by=doc.created_by,
                        created_user=doc.created_user,
                    )
                    new_doc = await sys_doc_service.create(obj=obj)

                # 更新 mbox 文件本身的记录
                content = f"这是一个 MBOX 邮箱文件，包含 {len(extracted_emails)} 封邮件。"
                obj_dict = {
                    'content': content,
                    'status': 1,  # Processed
                }
                await sys_doc_service.base_update(pk=doc.id, obj=obj_dict)
                return

            except Exception as e:
                log.error(f"处理 MBOX 文件时发生错误：{e}")
                traceback.print_exc()
                content = f"处理 MBOX 文件时发生错误：{str(e)}"
                obj_dict = {
                    'content': content,
                    'status': 1,
                }
                await sys_doc_service.base_update(pk=doc.id, obj=obj_dict)
                return

        if is_text_file(doc.file_suffix):
            # 在线程池中执行编码检测（chardet 是 CPU 密集型操作）
            content = await asyncio.to_thread(upload_service.decode_content_with_chardet, file_bytes)

        if is_excel_file(doc.file_suffix):
            content = await upload_service.read_excel_data(doc=doc, file_bytes=file_bytes)

        if is_csv_file(doc.file_suffix):
            content = await upload_service.read_csv_data(doc=doc, file_bytes=file_bytes)

        if is_parquet_file(doc.file_suffix):
            content = await upload_service.read_parquet_data(doc=doc, file_bytes=file_bytes)

        if is_email_file(doc.file_suffix):
            content = await upload_service.read_email_data(doc=doc, file_bytes=file_bytes)

        if is_picture_file(doc.file_suffix):
            content = "图片文件无法直接读取内容，请查看附件。"
            content = await upload_service.request_content(title=doc.title, file_bytes=file_bytes)

        if is_pdf_file(doc.file_suffix):
            try:
                content = await upload_service.request_content(title=doc.title, file_bytes=file_bytes)
                if content and len(content.strip()) > 0:
                    log.info(f"PDF文件 {doc.title} OCR 处理成功，内容长度: {len(content)}")
                else:
                    log.warning(f"PDF文件 {doc.title} OCR 返回内容为空，尝试使用 pdfplumber/PyPDF2 fallback")
                    raise ValueError("OCR 返回内容为空")
            except Exception as e:
                # OCR 调用失败，使用 pdfplumber/PyPDF2 作为 fallback
                log.warning(f"PDF文件 {doc.title} OCR 服务调用失败: {str(e)}，使用 pdfplumber/PyPDF2 fallback")
                pdf_text = await asyncio.to_thread(upload_service.extract_pdf_text, file_bytes)
                if pdf_text and len(pdf_text.strip()) > 0:
                    content = pdf_text
                    log.info(f"PDF文件 {doc.title} 使用 pdfplumber/PyPDF2 提取文字成功，长度: {len(content)}")
                else:
                    content = ''
                    log.error(f"PDF文件 {doc.title} OCR 和 pdfplumber/PyPDF2 均无法提取有效内容")

        if is_docx_file(doc.file_suffix) or is_media_file(doc.file_suffix) or is_pptx_file(doc.file_suffix):
            content = await upload_service.request_content(title=doc.title, file_bytes=file_bytes)

        # 其他文件方式的兜底方案
        if content == '':
            # 在线程池中执行编码检测
            content = await asyncio.to_thread(upload_service.decode_content_with_chardet, file_bytes)

        # 清理内容中的空字节和非法字符，避免 PostgreSQL 编码错误
        if content:
            content = upload_service.sanitize_text(content)
        if desc:
            desc = upload_service.sanitize_text(desc)

        obj_dict = {
            'content': content,
            'desc': desc,
        }
        await sys_doc_service.base_update(pk=doc.id, obj=obj_dict)

        # 异步调用 compute_embedding，不等待返回
        if content:
            asyncio.create_task(sys_doc_service.compute_embedding(id=doc.id))
            # 异步调用标签分类，自动为文档打标签
            asyncio.create_task(upload_service.auto_tag_document(doc_id=doc.id, content=content))

    @staticmethod
    async def auto_tag_document(doc_id: int, content: str):
        """
        自动为文档打标签

        :param doc_id: 文档ID
        :param content: 文档内容
        """
        try:
            # 调用标签分类函数获取匹配的标签
            tag_names = await classify_text_tags(content, threshold=0.5)
            if tag_names:
                # 为文档添加标签
                await tag_service.add_tags_to_doc(doc_id=doc_id, tag_names=tag_names)
                log.info(f"文档 {doc_id} 自动打标签完成: {tag_names}")
        except Exception as e:
            log.error(f"文档 {doc_id} 自动打标签失败: {str(e)}")

    @staticmethod
    def extract_pdf_text(file_bytes: bytes) -> str:
        """
        从 PDF 文件中提取文字内容（适用于文字型 PDF）

        :param file_bytes: PDF 文件的字节内容
        :return: 提取的文字内容，如果失败返回空字符串
        """
        text_content = ''

        # 尝试使用 pdfplumber（对中文支持较好）
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + '\n'
            if text_content.strip():
                return text_content.strip()
        except ImportError:
            log.warning("pdfplumber 未安装，尝试使用 PyPDF2")
        except Exception as e:
            log.warning(f"pdfplumber 提取失败: {str(e)}，尝试使用 PyPDF2")

        # 尝试使用 PyPDF2 作为备选
        try:
            import PyPDF2
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content += page_text + '\n'
            if text_content.strip():
                return text_content.strip()
        except ImportError:
            log.warning("PyPDF2 未安装")
        except Exception as e:
            log.warning(f"PyPDF2 提取失败: {str(e)}")

        return text_content.strip()

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

        # 清理文本中的空字节，避免 PostgreSQL 编码错误
        if subject:
            subject = upload_service.sanitize_text(subject)
        if body:
            body = upload_service.sanitize_text(body)
        if doc_name:
            doc_name = upload_service.sanitize_text(doc_name)

        # 提取真正的邮箱地址和名称
        from_name, from_email = EmailParser.extract_email_address(from_email_raw)
        # 处理多个收件人邮箱地址和名称
        to_emails_with_names = EmailParser.extract_multiple_emails_with_names(to_email_raw)
        cc_emails_with_names = EmailParser.extract_multiple_emails_with_names(cc_raw)
        bcc_emails_with_names = EmailParser.extract_multiple_emails_with_names(bcc_raw)

        # 用于msg_obj的字符串格式邮箱
        to_email = ', '.join([email for _, email in to_emails_with_names])
        cc = ', '.join([email for _, email in cc_emails_with_names])
        bcc = ', '.join([email for _, email in bcc_emails_with_names])

        # 获取附件信息，如果没有则设为空列表
        attachments = result_dict.get('attachments', [])

        # 从上下文中获取当前用户
        user = get_current_user()

        # 垃圾邮件检测
        detection_result, confidence_score, detection_reason = spam_detector.detect(
            subject=subject,
            body=body,
            sender=from_email
        )

        # 记录检测结果到日志
        if detection_result > 0:
            log.info(
                f"垃圾邮件检测 - 主题: {subject[:50]}... | "
                f"发件人: {from_email} | "
                f"结果: {'垃圾邮件' if detection_result == 1 else '疑似垃圾邮件'} | "
                f"置信度: {confidence_score:.1f} | "
                f"原因: {detection_reason}"
            )

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
            create_user=user.id if user else None,
            detection_result=detection_result,
        )
        await mail_msg_service.create(obj=msg_obj)

        # 处理发件人邮箱
        if from_email:
            from_box = await mail_box_service.get_by_name(name=from_email)  # 仍使用email作为唯一标识
            if from_box:
                await mail_box_service.base_update(pk=from_box.id, obj={'email_num': from_box.email_num + 1})
            else:
                country = EmailParser.extract_country(from_email)
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
                country = EmailParser.extract_country(email_addr)
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
                country = EmailParser.extract_country(email_addr)
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
                country = EmailParser.extract_country(email_addr)
                bcc_mail_obj = CreateMailBoxParam(
                    user_name=name,  # 使用提取的名称
                    name=email_addr,
                    email_num=1,
                    country=country,
                )
                await mail_box_service.create(obj=bcc_mail_obj)
        return f"{subject}\n {body}"



    @staticmethod
    async def do_read_email(doc: SysDoc, file_bytes: bytes):

        if not file_bytes:
            return None

        try:
            import datetime

            # 在线程池中执行同步的邮件解析
            email_data, attachment_list = await asyncio.to_thread(
                EmailParser.parse_email_sync, file_bytes
            )

            # 异步处理附件
            for att_data in attachment_list:
                # 异步上传到 MinIO
                await UploadService._minio_put_object(
                    bucket_name,
                    att_data['new_filename_minio'],
                    att_data['file_content_bytes'],
                    att_data['content_type']
                )

                obj = CreateSysDocParam(
                    title=att_data['filename'],
                    name=att_data['filename'],
                    type=att_data['file_type'],
                    file=att_data['new_filename_minio'],
                    uuid=att_data['unique_id'],
                    file_suffix=att_data['file_suffix'],
                    doc_time=datetime.datetime.now(),
                    size=len(att_data['file_content_bytes']),
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
                    'name': att_data['filename']
                })


                await sys_doc_service.create_doc_tokens(id=new_doc.id)

                await sys_doc_service.base_update(pk=new_doc.id, obj={
                    'status': 1,
                })

            return email_data

        except Exception as e:
            print(f"解析邮件时发生错误：{e}")
            raise e
        


    @staticmethod
    async def read_excel_data(doc: SysDoc, file_bytes: bytes):
        """读取 Excel 文件并保存数据"""
        # 使用 tabular_processor 读取 Excel
        data_json, content = await tabular_processor.read_excel(file_bytes)

        doc_id = doc.id
        obj_list = []
        for row_data in data_json:
            param = CreateSysDocDataParam(doc_id=doc_id, row=row_data)
            obj_list.append(param)
        await sys_doc_service.create_doc_data(obj_list=obj_list)
        return content

    @staticmethod
    async def read_csv_data(doc: SysDoc, file_bytes: bytes):
        """读取 CSV 文件并保存数据"""
        # 使用 tabular_processor 读取 CSV
        data_json, content = await tabular_processor.read_csv(file_bytes)

        doc_id = doc.id
        obj_list = []
        for row_data in data_json:
            param = CreateSysDocDataParam(doc_id=doc_id, row=row_data)
            obj_list.append(param)
        await sys_doc_service.create_doc_data(obj_list=obj_list)
        return content

    @staticmethod
    def _read_parquet_sync(file_bytes: bytes) -> tuple[list, str]:
        """同步读取 Parquet 文件，返回数据和内容字符串"""
        import pyarrow.parquet as pq

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
            # 使用 tabular_processor 的工具方法
            from backend.app.admin.utils.tabular_processor import TabularProcessor
            strings = TabularProcessor.dict_to_string(row_data)
            content += strings + '\n'

        data_json = df_sample.to_dict(orient="records")
        return data_json, content

    @staticmethod
    async def read_parquet_data(doc: SysDoc, file_bytes: bytes):
        # 在线程池中执行同步的 Parquet 读取操作
        data_json, content = await asyncio.to_thread(UploadService._read_parquet_sync, file_bytes)

        # 将数据保存到数据库
        doc_id = doc.id
        obj_list = []
        for row_data in data_json:
            param = CreateSysDocDataParam(doc_id=doc_id, row=row_data)
            obj_list.append(param)
        await sys_doc_service.create_doc_data(obj_list=obj_list)

        return content



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