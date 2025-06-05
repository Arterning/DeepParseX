
import sys

from anyio import run

sys.path.append('../')

from backend.app.admin.service.doc_service import sys_doc_service


async def test_build_visualize_knowledge_graph():
    doc = await sys_doc_service.get(pk=3)
    graph_data = sys_doc_service.build_visualize_knowledge_graph(triples=doc.doc_spos)
    print(graph_data)


async def test_follow_doc():
    res = await sys_doc_service.collect_doc(collecton_id=5, doc_id=58)
    print(res)

async def init() -> None:
    res = await sys_doc_service.build_graph(pk=3)
    print(res)
    

async def test_count_doc():
    res = await sys_doc_service.get_count()
    print(res)

if __name__ == '__main__':
    run(test_count_doc) 



