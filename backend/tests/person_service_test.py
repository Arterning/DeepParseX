
import sys

from anyio import run

sys.path.append('../')
from backend.app.admin.service.person_service import person_service

async def init() -> None:
    res = await person_service.get_subgraph(center_person_id=11)
    for r in res:
        print(r.person_id, r.other_id, r.relation_type)
    print(res)

if __name__ == '__main__':
    run(init) 