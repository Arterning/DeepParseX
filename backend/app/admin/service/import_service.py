#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
外部数据源导入服务
支持从多种数据源导入文件到系统中
"""

import os
import asyncio
import uuid
import mimetypes
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from io import BytesIO

from backend.common.log import log
from backend.app.admin.model import SysDoc
from backend.app.admin.schema.doc import CreateSysDocParam
from backend.app.admin.service.doc_service import sys_doc_service
from backend.app.admin.service.upload_service import upload_service
from backend.utils.upload_utils import get_file_suffix, get_file_type
from backend.utils.oss_client import minio_client
from backend.core.conf import settings
from backend.common.context import get_current_user


class ImportService:
    """外部数据源导入服务"""

    # ============ S3 数据源 ============
    @staticmethod
    async def import_from_s3(
        *,
        bucket_name: str,
        prefix: str = '',
        access_key: str = None,
        secret_key: str = None,
        endpoint_url: str = None,
        region: str = 'us-east-1',
        recursive: bool = True,
        doc_dir_id: int = None,
        dept_id: int = None,
        user_id: int = None,
        username: str = None
    ) -> Dict:
        """
        从 S3 导入文件

        Args:
            bucket_name: S3 桶名称
            prefix: 对象前缀（可以是文件路径或目录路径）
            access_key: AWS Access Key
            secret_key: AWS Secret Key
            endpoint_url: S3 端点 URL（用于兼容 MinIO 等 S3 兼容存储）
            region: AWS 区域
            recursive: 是否递归导入子目录
            doc_dir_id: 目标文档目录 ID
            dept_id: 部门 ID
            user_id: 用户 ID
            username: 用户名

        Returns:
            导入结果统计
        """
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError:
            raise ImportError("需要安装 boto3 库: pip install boto3")

        # 创建 S3 客户端
        s3_config = {
            'aws_access_key_id': access_key,
            'aws_secret_access_key': secret_key,
            'region_name': region
        }
        if endpoint_url:
            if not endpoint_url.startswith('http'):
                endpoint_url = f"http://{endpoint_url}"
            s3_config['endpoint_url'] = endpoint_url

        s3_client = boto3.client('s3', **s3_config)

        # 统计信息
        stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'errors': []
        }

        try:
            # 检查 prefix 是文件还是目录
            # 如果 prefix 以 / 结尾，则认为是目录；否则先检查是否存在该文件
            is_directory = prefix.endswith('/')

            if not is_directory:
                # 尝试作为单个文件处理
                try:
                    s3_client.head_object(Bucket=bucket_name, Key=prefix)
                    # 文件存在，导入单个文件
                    await ImportService._import_s3_file(
                        s3_client=s3_client,
                        bucket_name=bucket_name,
                        object_key=prefix,
                        doc_dir_id=doc_dir_id,
                        dept_id=dept_id,
                        user_id=user_id,
                        username=username,
                        stats=stats
                    )
                    return stats
                except ClientError:
                    # 文件不存在，作为目录处理
                    is_directory = True

            if is_directory:
                # 列出所有对象
                paginator = s3_client.get_paginator('list_objects_v2')
                pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

                for page in pages:
                    if 'Contents' not in page:
                        continue

                    for obj in page['Contents']:
                        object_key = obj['Key']

                        # 跳过目录本身
                        if object_key.endswith('/'):
                            continue

                        # 如果不是递归模式，跳过子目录中的文件
                        if not recursive:
                            relative_path = object_key[len(prefix):]
                            if '/' in relative_path:
                                continue

                        # 导入文件
                        await ImportService._import_s3_file(
                            s3_client=s3_client,
                            bucket_name=bucket_name,
                            object_key=object_key,
                            doc_dir_id=doc_dir_id,
                            dept_id=dept_id,
                            user_id=user_id,
                            username=username,
                            stats=stats
                        )

            return stats

        except Exception as e:
            log.error(f"从 S3 导入文件失败: {str(e)}")
            stats['errors'].append(f"导入失败: {str(e)}")
            return stats

    @staticmethod
    async def _import_s3_file(
        *,
        s3_client,
        bucket_name: str,
        object_key: str,
        doc_dir_id: int = None,
        dept_id: int = None,
        user_id: int = None,
        username: str = None,
        stats: Dict
    ):
        """导入单个 S3 文件"""
        try:
            stats['total'] += 1

            # 获取文件元数据
            obj_metadata = s3_client.head_object(Bucket=bucket_name, Key=object_key)

            # 下载文件内容
            response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
            file_bytes = response['Body'].read()

            # 获取文件名
            filename = os.path.basename(object_key)
            file_suffix = get_file_suffix(filename)
            file_type = get_file_type(file_suffix)

            # 生成唯一 ID 并上传到 MinIO
            unique_id = str(uuid.uuid4())
            new_filename = f"{unique_id}{file_suffix}"

            # 确保 bucket 存在
            await asyncio.to_thread(upload_service.ensure_bucket_exists, settings.BUCKET_NAME)

            # 上传到 MinIO
            content_type, _ = mimetypes.guess_type(filename)
            if content_type is None:
                content_type = 'application/octet-stream'

            await upload_service._minio_put_object(
                settings.BUCKET_NAME,
                new_filename,
                file_bytes,
                content_type
            )

            # 获取文件大小和修改时间
            file_size = obj_metadata.get('ContentLength', len(file_bytes))
            last_modified = obj_metadata.get('LastModified')

            # 创建文档记录
            obj = CreateSysDocParam(
                title=filename,
                name=filename,
                type=file_type,
                file=new_filename,
                uuid=unique_id,
                file_suffix=file_suffix,
                doc_time=last_modified,
                size=file_size,
                status=0,
                source=f"s3://{bucket_name}/{object_key}",
                doc_dir_id=doc_dir_id,
                dept_id=dept_id,
                created_by=user_id,
                created_user=username,
            )

            doc = await sys_doc_service.create(obj=obj)

            # 异步处理文件内容和索引
            asyncio.create_task(ImportService._process_imported_doc(doc.id))

            stats['success'] += 1
            log.info(f"成功导入 S3 文件: {object_key}")

        except Exception as e:
            stats['failed'] += 1
            error_msg = f"导入文件 {object_key} 失败: {str(e)}"
            stats['errors'].append(error_msg)
            log.error(error_msg)

    # ============ FTP/SFTP 数据源 ============
    @staticmethod
    async def import_from_ftp(
        *,
        host: str,
        port: int = 21,
        username: str = None,
        password: str = None,
        remote_path: str = '/',
        use_sftp: bool = False,
        recursive: bool = True,
        doc_dir_id: int = None,
        dept_id: int = None,
        user_id: int = None,
        current_username: str = None
    ) -> Dict:
        """
        从 FTP/SFTP 导入文件

        Args:
            host: FTP 服务器地址
            port: 端口号（FTP 默认 21，SFTP 默认 22）
            username: 用户名
            password: 密码
            remote_path: 远程路径（文件或目录）
            use_sftp: 是否使用 SFTP
            recursive: 是否递归导入子目录
            doc_dir_id: 目标文档目录 ID
            dept_id: 部门 ID
            user_id: 用户 ID
            current_username: 用户名

        Returns:
            导入结果统计
        """
        stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'errors': []
        }

        try:
            if use_sftp:
                # SFTP 导入
                try:
                    import paramiko
                except ImportError:
                    raise ImportError("需要安装 paramiko 库: pip install paramiko")

                # 在线程池中执行 SFTP 操作
                await asyncio.to_thread(
                    ImportService._import_from_sftp_sync,
                    host=host,
                    port=port or 22,
                    username=username,
                    password=password,
                    remote_path=remote_path,
                    recursive=recursive,
                    doc_dir_id=doc_dir_id,
                    dept_id=dept_id,
                    user_id=user_id,
                    current_username=current_username,
                    stats=stats
                )
            else:
                # FTP 导入
                await asyncio.to_thread(
                    ImportService._import_from_ftp_sync,
                    host=host,
                    port=port or 21,
                    username=username,
                    password=password,
                    remote_path=remote_path,
                    recursive=recursive,
                    doc_dir_id=doc_dir_id,
                    dept_id=dept_id,
                    user_id=user_id,
                    current_username=current_username,
                    stats=stats
                )

            return stats

        except Exception as e:
            log.error(f"从 FTP/SFTP 导入文件失败: {str(e)}")
            stats['errors'].append(f"导入失败: {str(e)}")
            return stats

    @staticmethod
    def _import_from_ftp_sync(
        host: str,
        port: int,
        username: str,
        password: str,
        remote_path: str,
        recursive: bool,
        doc_dir_id: int,
        dept_id: int,
        user_id: int,
        current_username: str,
        stats: Dict
    ):
        """同步方式从 FTP 导入"""
        from ftplib import FTP

        ftp = FTP()
        ftp.connect(host, port)
        ftp.login(username or '', password or '')

        try:
            # 检查是文件还是目录
            try:
                # 尝试获取文件
                file_bytes = BytesIO()
                ftp.retrbinary(f'RETR {remote_path}', file_bytes.write)
                file_bytes.seek(0)

                # 是文件，直接导入
                asyncio.run(ImportService._import_file_from_bytes(
                    filename=os.path.basename(remote_path),
                    file_bytes=file_bytes.read(),
                    source=f"ftp://{host}{remote_path}",
                    doc_dir_id=doc_dir_id,
                    dept_id=dept_id,
                    user_id=user_id,
                    username=current_username,
                    stats=stats
                ))
            except:
                # 是目录，列出文件
                ImportService._list_ftp_directory(
                    ftp=ftp,
                    path=remote_path,
                    host=host,
                    recursive=recursive,
                    doc_dir_id=doc_dir_id,
                    dept_id=dept_id,
                    user_id=user_id,
                    current_username=current_username,
                    stats=stats
                )
        finally:
            ftp.quit()

    @staticmethod
    def _import_from_sftp_sync(
        host: str,
        port: int,
        username: str,
        password: str,
        remote_path: str,
        recursive: bool,
        doc_dir_id: int,
        dept_id: int,
        user_id: int,
        current_username: str,
        stats: Dict
    ):
        """同步方式从 SFTP 导入"""
        import paramiko

        transport = paramiko.Transport((host, port))
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)

        try:
            # 检查是文件还是目录
            try:
                file_attr = sftp.stat(remote_path)
                if not file_attr.st_mode & 0o040000:  # 不是目录
                    # 下载文件
                    file_bytes = BytesIO()
                    sftp.getfo(remote_path, file_bytes)
                    file_bytes.seek(0)

                    asyncio.run(ImportService._import_file_from_bytes(
                        filename=os.path.basename(remote_path),
                        file_bytes=file_bytes.read(),
                        source=f"sftp://{host}{remote_path}",
                        doc_dir_id=doc_dir_id,
                        dept_id=dept_id,
                        user_id=user_id,
                        username=current_username,
                        stats=stats
                    ))
                else:
                    # 是目录
                    ImportService._list_sftp_directory(
                        sftp=sftp,
                        path=remote_path,
                        host=host,
                        recursive=recursive,
                        doc_dir_id=doc_dir_id,
                        dept_id=dept_id,
                        user_id=user_id,
                        current_username=current_username,
                        stats=stats
                    )
            except IOError:
                pass
        finally:
            sftp.close()
            transport.close()

    @staticmethod
    def _list_ftp_directory(
        ftp,
        path: str,
        host: str,
        recursive: bool,
        doc_dir_id: int,
        dept_id: int,
        user_id: int,
        current_username: str,
        stats: Dict
    ):
        """递归列出 FTP 目录"""
        ftp.cwd(path)
        items = ftp.nlst()

        for item in items:
            item_path = f"{path}/{item}".replace('//', '/')
            try:
                # 尝试进入目录
                ftp.cwd(item_path)
                # 是目录
                if recursive:
                    ImportService._list_ftp_directory(
                        ftp, item_path, host, recursive,
                        doc_dir_id, dept_id, user_id, current_username, stats
                    )
                ftp.cwd(path)
            except:
                # 是文件
                file_bytes = BytesIO()
                ftp.retrbinary(f'RETR {item}', file_bytes.write)
                file_bytes.seek(0)

                asyncio.run(ImportService._import_file_from_bytes(
                    filename=item,
                    file_bytes=file_bytes.read(),
                    source=f"ftp://{host}{item_path}",
                    doc_dir_id=doc_dir_id,
                    dept_id=dept_id,
                    user_id=user_id,
                    username=current_username,
                    stats=stats
                ))

    @staticmethod
    def _list_sftp_directory(
        sftp,
        path: str,
        host: str,
        recursive: bool,
        doc_dir_id: int,
        dept_id: int,
        user_id: int,
        current_username: str,
        stats: Dict
    ):
        """递归列出 SFTP 目录"""
        for item in sftp.listdir_attr(path):
            item_path = f"{path}/{item.filename}".replace('//', '/')

            if item.st_mode & 0o040000:  # 是目录
                if recursive:
                    ImportService._list_sftp_directory(
                        sftp, item_path, host, recursive,
                        doc_dir_id, dept_id, user_id, current_username, stats
                    )
            else:
                # 是文件
                file_bytes = BytesIO()
                sftp.getfo(item_path, file_bytes)
                file_bytes.seek(0)

                asyncio.run(ImportService._import_file_from_bytes(
                    filename=item.filename,
                    file_bytes=file_bytes.read(),
                    source=f"sftp://{host}{item_path}",
                    doc_dir_id=doc_dir_id,
                    dept_id=dept_id,
                    user_id=user_id,
                    username=current_username,
                    stats=stats
                ))

    # ============ 本地文件系统 ============
    @staticmethod
    async def import_from_local(
        *,
        local_path: str,
        recursive: bool = True,
        doc_dir_id: int = None,
        dept_id: int = None,
        user_id: int = None,
        username: str = None
    ) -> Dict:
        """
        从本地文件系统导入文件

        Args:
            local_path: 本地路径（文件或目录）
            recursive: 是否递归导入子目录
            doc_dir_id: 目标文档目录 ID
            dept_id: 部门 ID
            user_id: 用户 ID
            username: 用户名

        Returns:
            导入结果统计
        """
        stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'errors': []
        }

        path = Path(local_path)

        if not path.exists():
            stats['errors'].append(f"路径不存在: {local_path}")
            return stats

        try:
            if path.is_file():
                # 导入单个文件
                await ImportService._import_local_file(
                    file_path=path,
                    doc_dir_id=doc_dir_id,
                    dept_id=dept_id,
                    user_id=user_id,
                    username=username,
                    stats=stats
                )
            elif path.is_dir():
                # 导入目录
                if recursive:
                    for file_path in path.rglob('*'):
                        if file_path.is_file():
                            await ImportService._import_local_file(
                                file_path=file_path,
                                doc_dir_id=doc_dir_id,
                                dept_id=dept_id,
                                user_id=user_id,
                                username=username,
                                stats=stats
                            )
                else:
                    for file_path in path.glob('*'):
                        if file_path.is_file():
                            await ImportService._import_local_file(
                                file_path=file_path,
                                doc_dir_id=doc_dir_id,
                                dept_id=dept_id,
                                user_id=user_id,
                                username=username,
                                stats=stats
                            )

            return stats

        except Exception as e:
            log.error(f"从本地文件系统导入失败: {str(e)}")
            stats['errors'].append(f"导入失败: {str(e)}")
            return stats

    @staticmethod
    async def _import_local_file(
        *,
        file_path: Path,
        doc_dir_id: int = None,
        dept_id: int = None,
        user_id: int = None,
        username: str = None,
        stats: Dict
    ):
        """导入单个本地文件"""
        try:
            stats['total'] += 1

            # 读取文件
            file_bytes = await asyncio.to_thread(file_path.read_bytes)

            await ImportService._import_file_from_bytes(
                filename=file_path.name,
                file_bytes=file_bytes,
                source=f"local://{file_path}",
                last_modified=datetime.fromtimestamp(file_path.stat().st_mtime),
                doc_dir_id=doc_dir_id,
                dept_id=dept_id,
                user_id=user_id,
                username=username,
                stats=stats
            )

        except Exception as e:
            stats['failed'] += 1
            error_msg = f"导入文件 {file_path} 失败: {str(e)}"
            stats['errors'].append(error_msg)
            log.error(error_msg)

    # ============ HTTP/HTTPS URL ============
    @staticmethod
    async def import_from_url(
        *,
        url: str,
        filename: str = None,
        doc_dir_id: int = None,
        dept_id: int = None,
        user_id: int = None,
        username: str = None
    ) -> Dict:
        """
        从 URL 导入文件

        Args:
            url: 文件 URL
            filename: 文件名（如果不提供，从 URL 中提取）
            doc_dir_id: 目标文档目录 ID
            dept_id: 部门 ID
            user_id: 用户 ID
            username: 用户名

        Returns:
            导入结果统计
        """
        stats = {
            'total': 1,
            'success': 0,
            'failed': 0,
            'errors': []
        }

        try:
            import httpx

            # 下载文件
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                file_bytes = response.content

            # 如果没有提供文件名，从 URL 中提取
            if not filename:
                filename = os.path.basename(url.split('?')[0])
                if not filename or '.' not in filename:
                    filename = 'downloaded_file'

            await ImportService._import_file_from_bytes(
                filename=filename,
                file_bytes=file_bytes,
                source=url,
                doc_dir_id=doc_dir_id,
                dept_id=dept_id,
                user_id=user_id,
                username=username,
                stats=stats
            )

            return stats

        except Exception as e:
            stats['failed'] = 1
            error_msg = f"从 URL 导入失败: {str(e)}"
            stats['errors'].append(error_msg)
            log.error(error_msg)
            return stats

    # ============ 通用辅助方法 ============
    @staticmethod
    async def _import_file_from_bytes(
        *,
        filename: str,
        file_bytes: bytes,
        source: str,
        last_modified: datetime = None,
        doc_dir_id: int = None,
        dept_id: int = None,
        user_id: int = None,
        username: str = None,
        stats: Dict
    ):
        """从字节流导入文件的通用方法"""
        try:
            stats['total'] += 1

            # 获取文件信息
            file_suffix = get_file_suffix(filename)
            file_type = get_file_type(file_suffix)

            # 生成唯一 ID 并上传到 MinIO
            unique_id = str(uuid.uuid4())
            new_filename = f"{unique_id}{file_suffix}"

            # 确保 bucket 存在
            await asyncio.to_thread(upload_service.ensure_bucket_exists, settings.BUCKET_NAME)

            # 上传到 MinIO
            content_type, _ = mimetypes.guess_type(filename)
            if content_type is None:
                content_type = 'application/octet-stream'

            await upload_service._minio_put_object(
                settings.BUCKET_NAME,
                new_filename,
                file_bytes,
                content_type
            )

            # 创建文档记录
            obj = CreateSysDocParam(
                title=filename,
                name=filename,
                type=file_type,
                file=new_filename,
                uuid=unique_id,
                file_suffix=file_suffix,
                doc_time=last_modified,
                size=len(file_bytes),
                status=0,
                source=source,
                doc_dir_id=doc_dir_id,
                dept_id=dept_id,
                created_by=user_id,
                created_user=username,
            )

            doc = await sys_doc_service.create(obj=obj)

            # 异步处理文件内容和索引
            asyncio.create_task(ImportService._process_imported_doc(doc.id))

            stats['success'] += 1
            log.info(f"成功导入文件: {filename} from {source}")

        except Exception as e:
            stats['failed'] += 1
            error_msg = f"导入文件 {filename} 失败: {str(e)}"
            stats['errors'].append(error_msg)
            log.error(error_msg)

    @staticmethod
    async def _process_imported_doc(doc_id: int):
        """处理导入的文档（读取内容、创建索引）"""
        try:
            # 获取文档
            doc = await sys_doc_service.get(pk=doc_id)

            # 读取文件内容
            await upload_service.read_file_content(doc=doc)

            # 创建分词索引
            await sys_doc_service.create_doc_tokens(id=doc_id)

            # 更新状态为正常
            await sys_doc_service.base_update(pk=doc_id, obj={'status': 1})

            log.info(f"文档 {doc_id} 处理完成")

        except Exception as e:
            log.error(f"处理文档 {doc_id} 失败: {str(e)}")
            # 更新状态为出错
            await sys_doc_service.base_update(pk=doc_id, obj={
                'status': 2,
                'error_msg': str(e)
            })


import_service = ImportService()
