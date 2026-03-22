
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

def is_html_file(file_suffix: str) -> bool:
    return file_suffix in ['.html', '.htm']

def get_file_suffix(filename: str):
    """
    获取文件后缀
    :return:
    """
    return Path(filename).suffix.lower()


file_type_handlers = {
    'spreadsheet': lambda suffix: is_excel_file(suffix) or is_parquet_file(suffix) or is_csv_file(suffix),
    'image': is_picture_file,
    'media': is_media_file,
    'text': is_text_file,
    'email': lambda suffix: is_email_file(suffix) or is_mbox_file(suffix),
    'pdf': is_pdf_file,
    'document': is_docx_file,
    'ppt': is_pptx_file,
    'html': is_html_file,
    'archive': lambda suffix: is_zip_file(suffix) or is_rar_file(suffix) or is_7z_file(suffix),
}
def get_file_type(file_suffix: str):
    for file_type, handler in file_type_handlers.items():
        if handler(file_suffix):
            return file_type
    return 'text'