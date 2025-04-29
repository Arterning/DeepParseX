
import sys

from anyio import run

sys.path.append('../')

from backend.app.admin.service.doc_service import sys_doc_service

async def init() -> None:
    await sys_doc_service.create_doc_tokens(id=34)

if __name__ == '__main__':
    run(init) 