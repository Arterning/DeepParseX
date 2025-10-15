
import sys

from anyio import run

sys.path.append('../')

from backend.app.admin.service.upload_service import upload_service

async def compute_embedding():
    res = await upload_service.insert_text_embs(id=3)
    print(res)


if __name__ == '__main__':
    run(compute_embedding) 



