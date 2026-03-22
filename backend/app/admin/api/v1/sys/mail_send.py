#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件发送接口
通过系统配置的 SMTP 账户对外发送邮件，支持多收件人、抄送、附件。
"""
import asyncio
import smtplib
from email.headerregistry import Address
from email.message import EmailMessage
from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile

from backend.app.admin.crud.crud_config import config_dao
from backend.common.exception import errors
from backend.common.log import log
from backend.common.response.response_schema import ResponseModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db_pg import async_db_session

router = APIRouter()


async def _get_smtp_settings() -> dict:
    """从数据库读取最新 SMTP 配置，缺失必填项时抛出 ForbiddenError。"""
    async with async_db_session() as db:
        config = await config_dao.get_one(db)

    if not config or not config.settings:
        raise errors.ForbiddenError(msg='系统尚未配置 SMTP，请前往「系统配置 → 邮件发送配置」完成设置')

    s = config.settings
    host = s.get('SMTP_HOST', '').strip()
    if not host:
        raise errors.ForbiddenError(msg='SMTP 服务器地址未配置，请前往「系统配置 → 邮件发送配置」填写')

    user = s.get('SMTP_USER', '').strip()
    if not user:
        raise errors.ForbiddenError(msg='SMTP 用户名未配置')

    password = s.get('SMTP_PASSWORD', '').strip()
    if not password:
        raise errors.ForbiddenError(msg='SMTP 密码未配置')

    return {
        'host': host,
        'port': int(s.get('SMTP_PORT', 465)),
        'user': user,
        'password': password,
        'from_name': s.get('SMTP_FROM_NAME', '').strip() or '数据治理平台',
        'ssl_mode': s.get('SMTP_SSL', 'SSL'),  # 'SSL' | 'STARTTLS' | 'NONE'
    }


def _build_message(
    *,
    from_addr: str,
    from_name: str,
    to_list: list[str],
    cc_list: list[str],
    subject: str,
    body: str,
    attachments: list[tuple[str, bytes, str]],  # (filename, data, mime_type)
) -> EmailMessage:
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = f'{from_name} <{from_addr}>'
    msg['To'] = ', '.join(to_list)
    if cc_list:
        msg['Cc'] = ', '.join(cc_list)

    msg.set_content(body)

    for filename, data, mime_type in attachments:
        maintype, subtype = mime_type.split('/', 1) if '/' in mime_type else ('application', 'octet-stream')
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=filename)

    return msg


def _send_sync(cfg: dict, msg: EmailMessage) -> None:
    """同步发送邮件，在线程池中调用。"""
    host, port, user, password, ssl_mode = (
        cfg['host'], cfg['port'], cfg['user'], cfg['password'], cfg['ssl_mode']
    )
    recipients = msg.get_all('To', []) + msg.get_all('Cc', [])

    try:
        if ssl_mode == 'SSL':
            with smtplib.SMTP_SSL(host, port, timeout=15) as smtp:
                smtp.login(user, password)
                smtp.send_message(msg)

        elif ssl_mode == 'STARTTLS':
            with smtplib.SMTP(host, port, timeout=15) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(user, password)
                smtp.send_message(msg)

        else:  # NONE
            with smtplib.SMTP(host, port, timeout=15) as smtp:
                smtp.login(user, password)
                smtp.send_message(msg)

    except smtplib.SMTPAuthenticationError:
        raise ValueError('SMTP 认证失败，请检查用户名和密码（或授权码）')
    except smtplib.SMTPConnectError:
        raise ValueError(f'无法连接到 SMTP 服务器 {host}:{port}，请检查地址和端口')
    except smtplib.SMTPRecipientsRefused as e:
        refused = ', '.join(e.recipients.keys())
        raise ValueError(f'以下收件人地址被拒绝：{refused}')
    except TimeoutError:
        raise ValueError(f'连接 SMTP 服务器超时（{host}:{port}）')


@router.post('/send', summary='发送邮件', dependencies=[DependsJwtAuth])
async def send_mail(
    to: Annotated[str, Form(description='收件人，多个地址用英文逗号分隔')],
    subject: Annotated[str, Form(description='邮件主题')],
    body: Annotated[str, Form(description='邮件正文')],
    cc: Annotated[str | None, Form(description='抄送，多个地址用英文逗号分隔')] = None,
    attachments: list[UploadFile] = File(default=[]),
) -> ResponseModel:
    """
    通过系统 SMTP 配置发送邮件。

    - **to**: 收件人，多个地址用英文逗号分隔
    - **cc**: 抄送（可选）
    - **subject**: 主题
    - **body**: 正文（纯文本）
    - **attachments**: 附件（可选，最多 10 个，每个 ≤ 50 MB）
    """
    # --- 读取 SMTP 配置 ---
    cfg = await _get_smtp_settings()

    # --- 解析地址列表 ---
    to_list = [addr.strip() for addr in to.split(',') if addr.strip()]
    cc_list = [addr.strip() for addr in (cc or '').split(',') if addr.strip()]

    if not to_list:
        raise errors.RequestError(msg='收件人不能为空')

    if len(attachments) > 10:
        raise errors.RequestError(msg='附件数量不能超过 10 个')

    # --- 读取附件内容 ---
    MAX_SIZE = 50 * 1024 * 1024  # 50 MB
    attachment_data: list[tuple[str, bytes, str]] = []
    for upload in attachments:
        if not upload.filename:
            continue
        data = await upload.read()
        if len(data) > MAX_SIZE:
            raise errors.RequestError(msg=f'附件 "{upload.filename}" 超过 50 MB 限制')
        mime = upload.content_type or 'application/octet-stream'
        attachment_data.append((upload.filename, data, mime))

    # --- 构建邮件 ---
    msg = _build_message(
        from_addr=cfg['user'],
        from_name=cfg['from_name'],
        to_list=to_list,
        cc_list=cc_list,
        subject=subject,
        body=body,
        attachments=attachment_data,
    )

    # --- 异步发送（在线程池中运行阻塞的 smtplib） ---
    try:
        await asyncio.to_thread(_send_sync, cfg, msg)
    except ValueError as e:
        log.warning(f'发送邮件失败: {e}')
        raise errors.RequestError(msg=str(e))
    except Exception as e:
        import traceback
        log.error(f'发送邮件时发生未知错误: {repr(e)}\n{traceback.format_exc()}')
        raise errors.ServerError(msg=f'邮件发送失败：{repr(e)}')

    log.info(f'邮件已发送 -> {to_list}，主题: {subject}，附件: {len(attachment_data)} 个')
    return response_base.success(data={'message': f'邮件已成功发送至 {", ".join(to_list)}'})
