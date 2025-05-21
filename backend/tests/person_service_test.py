
import sys
import networkx as nx
from anyio import run

sys.path.append('../')
from backend.app.admin.service.person_service import person_service

async def get_relation_list():
    res = await person_service.get_relations(center_person_id=11)
    for r in res:
        print(r.person_id, r.other_id, r.relation_type)
    print(res)
    person_ids = {p for edge in res for p in edge}
    print(tuple(person_ids))
    print(list(person_ids))

async def get_relation_graph():
    res = await person_service.get_subgraph(center_person_id=11)
    graph = res['graph']
    path = nx.shortest_path(graph, 11, 19)
    print("path", path)


async def init() -> None:
    await get_relation_graph()
    pass

if __name__ == '__main__':
    run(init) 