
import sys

from anyio import run

sys.path.append('../')
from backend.app.admin.service.scheduler_service import scheduler_service

async def init() -> None:

    res = await scheduler_service.auto_generate_summary_and_translation()
    
    print(res)

if __name__ == '__main__':
    run(init) 