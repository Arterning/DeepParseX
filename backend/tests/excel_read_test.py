
import sys

from anyio import run

sys.path.append('../')
from backend.app.admin.service.doc_service import sys_doc_service
from backend.app.admin.service.upload_service import upload_service

async def init() -> None:
    file_location = 'uploads/16-20 民用汽车拥有量.xls'
    doc = await sys_doc_service.get(pk=39)
    file_bytes = None
    try:
        with open(file_location, 'rb') as file:
            file_bytes = file.read()
            await upload_service.read_excel_data(doc, file_bytes)
    except Exception as e:
        print(f"读取文件时发生错误：{e}")
        raise e


if __name__ == '__main__':
    run(init) 