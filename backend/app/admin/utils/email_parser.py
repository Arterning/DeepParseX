#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
邮件解析工具类
提供邮件地址提取、邮件文件解析等功能
"""

import uuid
import io
import tempfile
import os
import mailbox
from email.parser import BytesParser
from email.policy import default
import email.utils
import datetime as dt_module
import mimetypes

from backend.common.log import log
from backend.utils.upload_utils import get_file_suffix, get_file_type


class EmailParser:
    """邮件解析工具类"""

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
    def parse_email_sync(file_bytes: bytes) -> tuple[dict, list]:
        """
        同步解析邮件，返回邮件数据和附件列表

        Args:
            file_bytes: 邮件文件的字节内容

        Returns:
            tuple[dict, list]: (邮件数据字典, 附件列表)
        """
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
                date_tuple = email.utils.parsedate_tz(email_data['date'])
                if date_tuple:
                    timestamp = email.utils.mktime_tz(date_tuple)
                    dt = dt_module.datetime.fromtimestamp(timestamp)
                    email_data['parsed_date'] = dt
            except Exception as e:
                log.warning(f"解析日期时发生错误: {e}")
                email_data['parsed_date'] = None

        # 获取邮件正文
        email_data['body'] = ''
        plain_text = None
        html_content = None

        # 附件列表
        attachment_list = []

        # 获取邮件内容
        if msg.is_multipart():
            for part in msg.walk():
                content_disposition = str(part.get("Content-Disposition", ""))
                filename = part.get_filename()
                content_type = str(part.get_content_type())

                is_attachment = ("attachment" in content_disposition or
                                (filename and not content_type.startswith('text/')))

                if is_attachment and filename:
                    file_content_bytes = part.get_payload(decode=True)
                    unique_id = str(uuid.uuid4())
                    file_suffix = get_file_suffix(filename)
                    new_filename_minio = f"{unique_id}{file_suffix}"
                    content_type_mime, _ = mimetypes.guess_type(filename)
                    if content_type_mime is None:
                        content_type_mime = 'application/octet-stream'
                    attachment_list.append({
                        'filename': filename,
                        'file_content_bytes': file_content_bytes,
                        'unique_id': unique_id,
                        'file_suffix': file_suffix,
                        'new_filename_minio': new_filename_minio,
                        'content_type': content_type_mime,
                        'file_type': get_file_type(file_suffix),
                    })
                    continue

                content_type = part.get_content_type()
                if content_type == "text/plain" and not plain_text:
                    plain_text = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='replace')
                elif content_type == "text/html" and not html_content:
                    html_content = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='replace')
        else:
            content_type = msg.get_content_type()
            if content_type == "text/plain":
                plain_text = msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', errors='replace')
            elif content_type == "text/html":
                html_content = msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', errors='replace')

        email_data['body'] = plain_text or html_content or ''

        # 清理文本中的空字节，避免 PostgreSQL 编码错误
        def _sanitize(text):
            if text:
                return text.replace('\x00', '').encode('utf-8', errors='ignore').decode('utf-8')
            return text

        email_data['subject'] = _sanitize(email_data.get('subject', ''))
        email_data['body'] = _sanitize(email_data.get('body', ''))
        # 清理附件文件名
        for att in attachment_list:
            att['filename'] = _sanitize(att.get('filename', ''))

        return email_data, attachment_list

    @staticmethod
    def extract_mbox_emails_sync(file_bytes: bytes) -> list[dict]:
        """
        同步解析 mbox 文件，返回邮件信息列表

        Args:
            file_bytes: mbox 文件的字节内容

        Returns:
            list[dict]: 邮件信息列表
        """
        extracted_emails = []
        # 创建临时文件来存储 mbox 内容
        with tempfile.NamedTemporaryFile(suffix='.mbox', delete=False) as temp_file:
            temp_file.write(file_bytes)
            temp_file_path = temp_file.name
        try:
            mbox = mailbox.mbox(temp_file_path)
            email_count = 0
            for message in mbox:
                email_count += 1
                email_bytes = message.as_bytes()
                subject = message.get('Subject', f'邮件_{email_count}')
                if not subject:
                    subject = f'邮件_{email_count}'
                # 清理 subject 中的空字节
                if subject:
                    subject = subject.replace('\x00', '').encode('utf-8', errors='ignore').decode('utf-8')
                unique_id = str(uuid.uuid4())
                new_filename_minio = f"{unique_id}.eml"
                extracted_emails.append({
                    'subject': subject,
                    'email_bytes': email_bytes,
                    'unique_id': unique_id,
                    'new_filename_minio': new_filename_minio,
                })
        finally:
            os.unlink(temp_file_path)
        return extracted_emails


# 创建全局实例
email_parser = EmailParser()
