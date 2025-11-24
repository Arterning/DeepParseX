
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from pathlib import Path
import os


def is_zip_file(file_suffix: str) -> bool:
    return file_suffix in ['.zip']

def is_rar_file(file_suffix: str) -> bool:
    return file_suffix in ['.rar']

def is_7z_file(file_suffix: str) -> bool:
    return file_suffix in ['.7z']

def is_compressed_file(file_suffix: str) -> bool:
    """判断是否为常见的压缩包文件"""
    return is_zip_file(file_suffix) or is_rar_file(file_suffix) or is_7z_file(file_suffix)

def is_excel_file(file_suffix: str) -> bool:
    return file_suffix in ['.xls', '.xlsx', '.csv']

def is_csv_file(file_suffix: str) -> bool:
    return file_suffix in ['.csv']

def is_pdf_file(file_suffix: str) -> bool:
    return file_suffix in ['.pdf']

def is_picture_file(file_suffix: str) -> bool:
    return file_suffix in ['.jpeg', '.jpg', '.png']

def is_media_file(file_suffix: str) -> bool:
    return file_suffix in ['.mp4', '.mp3', '.flv', '.wav']

def is_text_file(file_suffix: str) -> bool:
    return file_suffix in ['.txt', '.host', '.config', '.md',
                                             '.c', '.cpp', '.java', '.py', 'js', '.ts', '.rb', '.go']
def is_email_file(file_suffix: str) -> bool:
    return file_suffix in ['.eml']

def is_mbox_file(file_suffix: str) -> bool:
    return file_suffix in ['.mbox']

def is_docx_file(file_suffix: str) -> bool:
    return file_suffix in ['.docx', '.doc']

def is_pptx_file(file_suffix: str) -> bool:
    return file_suffix in ['.pptx', '.ppt']

def is_parquet_file(file_suffix: str) -> bool:
    return file_suffix in ['.parquet']


def get_file_suffix(filename: str):
    """
    获取文件后缀
    :return:
    """
    return Path(filename).suffix.lower()


file_type_handlers = {
    '表格': lambda suffix: is_excel_file(suffix) or is_parquet_file(suffix),
    '图片': is_picture_file,
    '媒体': is_media_file,
    '文本': is_text_file,
    '邮件': lambda suffix: is_email_file(suffix) or is_mbox_file(suffix),
    'PDF': is_pdf_file,
    '文档': is_docx_file,
    'PPT': is_pptx_file,
    '压缩包': lambda suffix: is_zip_file(suffix) or is_rar_file(suffix)
}
def get_file_type(file_suffix: str):
    for file_type, handler in file_type_handlers.items():
        if handler(file_suffix):
            # print("匹配到文件类型:", file_type)
            return file_type
    # print("未匹配到文件类型，默认返回文本")
    return '文本'