
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
    graph = await person_service.get_subgraph(center_person_id=11)
    path = nx.shortest_path(graph, 11, 19)
    print("path", path)


async def get_full_relation_graph():
    res = await person_service.get_full_graph()
    graph = res['graph']
    path = nx.shortest_path(graph, 11, 19)
    print("path", path)


async def get_shortest_path():
    res = await person_service.get_full_graph()
    graph = res['graph']
    res = person_service.find_shortest_path(graph=graph, person1_id=11, person2_id=19)
    print(res)

async def analyze_network():
    res = await person_service.get_full_graph()
    graph = res['graph']
    res = person_service.analyze_network(graph=graph, person_id=11)
    print(res)


async def find_common_connections():
    res = await person_service.get_full_graph()
    graph = res['graph']
    res = person_service.find_common_connections(graph=graph, person1_id=11, person2_id=19)
    print(res)

async def init() -> None:
    await find_common_connections()
    pass

if __name__ == '__main__':
    run(init) 