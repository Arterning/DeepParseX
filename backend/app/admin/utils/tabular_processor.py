#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
表格文件处理器
支持 Excel (.xls, .xlsx) 和 CSV (.csv) 文件的读取和处理
"""

from io import BytesIO
import pandas as pd
import numpy as np
from backend.common.log import log


class TabularProcessor:
    """表格文件处理器类"""

    @staticmethod
    def dict_to_string(input_dict: dict) -> str:
        """将字典转换为字符串格式"""
        return ' '.join(f"{key} {value}" for key, value in input_dict.items())

    @staticmethod
    def _read_excel_sync(file_bytes: bytes) -> tuple[list, str]:
        """
        同步读取 Excel 文件，返回数据和内容字符串

        :param file_bytes: Excel 文件的字节内容
        :return: (数据列表, 内容字符串)
        """
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
        for row_data in data_json:
            strings = TabularProcessor.dict_to_string(row_data)
            row = strings + '\n'
            content += row
        content = content.replace("Unnamed", "").replace("None", "")

        return data_json, content

    @staticmethod
    def _read_csv_sync(file_bytes: bytes) -> tuple[list, str]:
        """
        同步读取 CSV 文件，返回数据和内容字符串

        :param file_bytes: CSV 文件的字节内容
        :return: (数据列表, 内容字符串)
        """
        import chardet

        # 使用 chardet 检测编码
        result = chardet.detect(file_bytes)
        encoding = result.get('encoding', 'utf-8')

        log.info(f"CSV 文件编码检测: {encoding}")

        # 常见的中文编码兼容处理
        if encoding and encoding.lower() in ['gb2312', 'gbk', 'gb18030']:
            # 优先尝试 GB18030，因为它是最全面的
            for enc in ['gb18030', 'gbk', 'gb2312']:
                try:
                    df = pd.read_csv(BytesIO(file_bytes), encoding=enc)
                    log.info(f"使用 {enc} 编码成功读取 CSV")
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            else:
                # 如果都失败，使用 utf-8 并忽略错误
                df = pd.read_csv(BytesIO(file_bytes), encoding='utf-8', encoding_errors='ignore')
        else:
            # 尝试使用检测到的编码
            try:
                df = pd.read_csv(BytesIO(file_bytes), encoding=encoding)
            except (UnicodeDecodeError, LookupError):
                # 失败则尝试常见编码
                for fallback_enc in ['utf-8', 'gb18030', 'gbk', 'latin-1']:
                    try:
                        df = pd.read_csv(BytesIO(file_bytes), encoding=fallback_enc)
                        log.info(f"使用 {fallback_enc} 编码成功读取 CSV")
                        break
                    except (UnicodeDecodeError, LookupError):
                        continue
                else:
                    # 最后使用 UTF-8 忽略错误
                    df = pd.read_csv(BytesIO(file_bytes), encoding='utf-8', encoding_errors='ignore')

        # 替换 NaN 为 None（可以避免 PostgreSQL 插入错误）
        df = df.where(pd.notnull(df), None)
        df.replace([np.nan, np.inf, -np.inf], None, inplace=True)

        # 将 DataFrame 转换为 JSON 格式
        data_json = df.to_dict(orient="records")

        content = ''
        for row_data in data_json:
            strings = TabularProcessor.dict_to_string(row_data)
            row = strings + '\n'
            content += row
        content = content.replace("Unnamed", "").replace("None", "")

        return data_json, content

    @staticmethod
    async def read_excel(file_bytes: bytes):
        """
        异步读取 Excel 文件

        :param file_bytes: Excel 文件的字节内容
        :return: (数据列表, 内容字符串)
        """
        import asyncio
        return await asyncio.to_thread(TabularProcessor._read_excel_sync, file_bytes)

    @staticmethod
    async def read_csv(file_bytes: bytes):
        """
        异步读取 CSV 文件

        :param file_bytes: CSV 文件的字节内容
        :return: (数据列表, 内容字符串)
        """
        import asyncio
        return await asyncio.to_thread(TabularProcessor._read_csv_sync, file_bytes)


# 创建全局实例
tabular_processor = TabularProcessor()
