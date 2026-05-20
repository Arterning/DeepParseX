#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import aiohttp

from backend.common.log import log
from backend.app.admin.service.config_service import config_service


async def process_file(file_name: str, file_data: bytes, task: str = '默认算法'):
    """
    向 OCR 服务发送文件，获取处理后的结果。

    :param file_name: 文件名
    :param file_data: 文件二进制数据
    :param task: OCR 任务类型，默认 '默认算法'，双页排版传 'spread'
    :return: OCR 服务返回的 JSON 结果
    """
    merged_settings = await config_service.get_merged_settings()
    url = merged_settings.OCR_URL

    try:
        form_data = aiohttp.FormData()
        form_data.add_field('file', file_data, filename=file_name, content_type='application/octet-stream')
        form_data.add_field('task', task)

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=form_data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    log.error(f"[process_file] OCR 请求失败，状态码：{response.status}，错误：{error_text}")
                    return {"content": error_text}

    except Exception as e:
        log.error(f"[process_file] 中出现错误：{repr(e)}")
        return str(e)


class OcrService:

    @staticmethod
    async def extract_content(title: str, file_bytes: bytes, ocr_task: str = '默认算法'):
        response = await process_file(title, file_bytes, task=ocr_task)
        if not response or 'content' not in response:
            return "", []
        raw_content = response.get('content', '')
        ocr_pages = response.get('pages_content', [])
        clean_content = raw_content.replace('\x00', '').encode('utf-8', errors='ignore').decode('utf-8')
        pages = []
        if isinstance(ocr_pages, list):
            for i, page_text in enumerate(ocr_pages):
                pages.append({
                    'page': i + 1,
                    'text': page_text,
                })
        return clean_content, pages


ocr_service = OcrService()
