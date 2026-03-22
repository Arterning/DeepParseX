
import sys

from anyio import run

sys.path.append('../')
from backend.app.admin.service.scheduler_service import scheduler_service

async def init() -> None:

    res = await scheduler_service.run_hourly_pipeline()
    
    print(res)

if __name__ == '__main__':
    run(init) 