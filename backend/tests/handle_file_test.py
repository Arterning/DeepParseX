
import sys

from anyio import run

sys.path.append('../')

from backend.app.admin.service.upload_service import upload_service

async def init() -> None:
    await upload_service.handle_file(id=13)

if __name__ == '__main__':
    run(init) 