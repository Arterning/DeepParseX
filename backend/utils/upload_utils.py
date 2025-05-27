
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from pathlib import Path
import os


def is_zip_file(file_suffix: str) -> bool:
    return file_suffix in ['.zip']

def is_excel_file(file_suffix: str) -> bool:
    return file_suffix in ['.xls', '.xlsx']

def is_csv_file(file_suffix: str) -> bool:
    return file_suffix in ['.csv']

def is_pdf_file(file_suffix: str) -> bool:
    return file_suffix in ['.pdf']

def is_picture_file(file_suffix: str) -> bool:
    return file_suffix in ['.jpeg', '.jpg', '.png']

def is_media_file(file_suffix: str) -> bool:
    return file_suffix in ['.mp4', '.mp3', '.flv', '.wav']

def is_text_file(file_suffix: str) -> bool:
    return file_suffix in ['.txt', '.host', '.config',
                                             '.c', '.cpp', '.java', '.py', 'js', '.ts', '.rb', '.go']
def is_email_file(file_suffix: str) -> bool:
    return file_suffix in ['.eml']



def get_file_suffix(filename: str):
    """
    获取文件后缀
    :return:
    """
    return Path(filename).suffix.lower()


file_type_handlers = {
    '表格': is_excel_file,
    '表格': is_csv_file,
    '图片': is_picture_file,
    '媒体': is_media_file,
    '文本': is_text_file,
    '邮件': is_email_file,
    'PDF': is_pdf_file,
    '压缩包': is_zip_file
}
def get_file_type(file_suffix: str):
    for file_type, handler in file_type_handlers.items():
        if handler(file_suffix):
            return file_type
    return '文本'