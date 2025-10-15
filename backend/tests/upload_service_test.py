
import sys

from anyio import run

sys.path.append('../')

from backend.app.admin.service.upload_service import upload_service

async def compute_embedding():
    pass


if __name__ == '__main__':
    run(compute_embedding) 



