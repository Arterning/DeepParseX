
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from pathlib import Path
import os


def is_zip_file(file_suffix: str) -> bool:
    return file_suffix in ['zip']

def is_excel_file(file_suffix: str) -> bool:
    return file_suffix in ['xls', 'xlsx']

def is_csv_file(file_suffix: str) -> bool:
    return file_suffix in ['csv']

def is_pdf_file(file_suffix: str) -> bool:
    return file_suffix in ['pdf']

def is_picture_file(file_suffix: str) -> bool:
    return file_suffix in ['jpeg', 'jpg', 'png']

def is_media_file(file_suffix: str) -> bool:
    return file_suffix in ['mp4', 'mp3', 'flv', 'wav']

def is_text_file(file_suffix: str) -> bool:
    return file_suffix in ['txt', 'host', 'config',
                                             'c', 'cpp', 'java', 'py', 'js', 'ts', 'rb', 'go']
def is_email_file(file_suffix: str) -> bool:
    return file_suffix in ['eml']


def get_file_suffix(filename: str):
    """
    获取文件后缀
    :return:
    """
    return Path(filename).suffix.lower()


file_type_handlers = {
    'excel': is_excel_file,
    'csv': is_csv_file,
    'picture': is_picture_file,
    'media': is_media_file,
    'text': is_text_file,
    'email': is_email_file,
    'pdf': is_pdf_file,
    'zip': is_zip_file
}
def get_file_type(file_suffix: str):
    for file_type, handler in file_type_handlers.items():
        if handler(file_suffix):
            return file_type
    return 'text'