
import sys

from anyio import run

sys.path.append('../')
from backend.app.admin.service.doc_service import sys_doc_service

async def init() -> None:

    res = await sys_doc_service.auto_extract_entities_for_docs()
    
    print(res)

if __name__ == '__main__':
    run(init) 