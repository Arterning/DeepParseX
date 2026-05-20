#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
表格文件处理器
支持 Excel (.xls, .xlsx) 和 CSV (.csv) 文件的读取和处理
"""

import json
import uuid
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

        # 将 pandas/numpy 类型转换为 JSON 可序列化的 Python 原生类型
        for row_data in data_json:
            for key, val in row_data.items():
                row_data[key] = TabularProcessor._to_cell_value(val)

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

        # 将 pandas/numpy 类型转换为 JSON 可序列化的 Python 原生类型
        for row_data in data_json:
            for key, val in row_data.items():
                row_data[key] = TabularProcessor._to_cell_value(val)

        content = ''
        for row_data in data_json:
            strings = TabularProcessor.dict_to_string(row_data)
            row = strings + '\n'
            content += row
        content = content.replace("Unnamed", "").replace("None", "")

        return data_json, content

    @staticmethod
    def _to_cell_value(val):
        """
        将 pandas/numpy 值转换为 JSON 可序列化的 Python 原始类型。

        注意：numpy >= 2.0 的整数/浮点类型不再是 Python int/float 的子类，
        必须先调用 .item() 转换为 Python 原生类型，再做 isinstance 判断。
        """
        if val is None:
            return None
        # 先把 numpy scalar 转成 Python 原生类型（兼容 numpy 1.x / 2.x）
        if hasattr(val, 'item'):
            try:
                val = val.item()
            except (ValueError, TypeError):
                return str(val)
        # 经过 .item() 后 val 已经是 Python 原生类型
        if isinstance(val, bool):
            return val
        if isinstance(val, float):
            if val != val or val == float('inf') or val == float('-inf'):  # NaN / Inf
                return None
            return val
        if isinstance(val, int):
            return val
        if isinstance(val, str):
            return val if val.strip() not in ('', 'nan', 'None', 'NaT', 'NA', '<NA>') else None
        # pandas Timestamp / datetime → ISO 字符串
        if hasattr(val, 'isoformat'):
            try:
                return val.isoformat()
            except Exception:
                return str(val)
        return str(val)

    @staticmethod
    def data_to_workbook(data_json: list[dict], sheet_name: str = 'Sheet1') -> str:
        """
        将行数据列表（每行为 {列名: 值} 的 dict）转换为 Univer IWorkbookData JSON 字符串。

        - 第 0 行写列名（表头）
        - 第 1 行起写数据
        - 空值（None）跳过，不创建单元格
        """
        cell_data: dict[str, dict] = {}

        if not data_json:
            headers: list = []
        else:
            headers = list(data_json[0].keys())

        # 表头行：列名同样经过 _to_cell_value，避免 numpy / 非字符串列名导致序列化失败
        if headers:
            cell_data['0'] = {}
            for col_idx, header in enumerate(headers):
                hv = TabularProcessor._to_cell_value(header)
                cell_data['0'][str(col_idx)] = {'v': hv if hv is not None else str(header)}

        # 数据行
        for row_idx, row in enumerate(data_json, start=1):
            row_cells: dict[str, dict] = {}
            for col_idx, header in enumerate(headers):
                v = TabularProcessor._to_cell_value(row.get(header))
                if v is not None:
                    row_cells[str(col_idx)] = {'v': v}
            if row_cells:
                cell_data[str(row_idx)] = row_cells

        workbook = {
            'id': f'wb-{uuid.uuid4().hex[:8]}',
            'name': 'Workbook',
            'sheetOrder': ['sheet1'],
            'sheets': {
                'sheet1': {
                    'id': 'sheet1',
                    'name': sheet_name,
                    'cellData': cell_data,
                    'rowCount': max(100, len(data_json) + 10),
                    'columnCount': max(26, len(headers) + 2),
                }
            },
            'styles': {},
        }
        # default=str 作为最后兜底，防止残余的非序列化类型导致崩溃
        return json.dumps(workbook, ensure_ascii=False, default=str)

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
