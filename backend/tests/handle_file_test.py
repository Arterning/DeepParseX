
import sys

from anyio import run

sys.path.append('../')

from backend.app.admin.service.doc_service import sys_doc_service
from backend.app.admin.service.upload_service import upload_service

async def init() -> None:
    doc = await sys_doc_service.get(pk=56)
    await upload_service.read_file_content(doc=doc)

if __name__ == '__main__':
    run(init) 