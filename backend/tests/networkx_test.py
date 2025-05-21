import networkx as nx

# 创建有向图
G = nx.DiGraph()

# 添加节点（人物）
people = ["张三", "李四", "王五", "赵六", "钱七", "孙八"]
G.add_nodes_from(people)

# 添加边（关系）
relationships = [
    ("张三", "李四", {"relation": "同事"}),
    ("张三", "王五", {"relation": "朋友"}),
    ("李四", "赵六", {"relation": "亲戚"}),
    ("王五", "钱七", {"relation": "同学"}),
    ("钱七", "孙八", {"relation": "夫妻"})
]
G.add_edges_from(relationships)


def check_direct_relation(G, person1, person2):
    """检查两个人是否有直接关系"""
    if G.has_edge(person1, person2):
        return G.edges[person1, person2]['relation']
    elif G.has_edge(person2, person1):
        return G.edges[person2, person1]['relation']
    return None

# 间接关系查询（查找所有路径）
def find_all_relations(G, source, target, max_depth=4):
    """查找两个人之间的所有可能关系路径"""
    try:
        paths = nx.all_simple_paths(G, source=source, target=target, cutoff=max_depth)
        results = []
        for path in paths:
            relations = []
            for i in range(len(path)-1):
                relations.append(G.edges[path[i], path[i+1]]['relation'])
            results.append((path, relations))
        return results
    except nx.NetworkXNoPath:
        return []

def find_shortest_relation(G, source, target):
    """查找两人之间的最短关系路径"""
    try:
        path = nx.shortest_path(G, source=source, target=target)
        relations = []
        for i in range(len(path)-1):
            relations.append(G.edges[path[i], path[i+1]]['relation'])
        return path, relations
    except nx.NetworkXNoPath:
        return None, None


# 示例查询
print(check_direct_relation(G, "张三", "李四"))  # 输出: 同事
print(check_direct_relation(G, "李四", "张三"))  


# 示例查询
relations = find_all_relations(G, "张三", "孙八")
for path, rels in relations:
    print(f"路径: {' -> '.join(path)}")
    print(f"关系链: {' -> '.join(rels)}\n")

# 示例查询
path, rels = find_shortest_relation(G, "张三", "孙八")
print(f"最短路径: {' -> '.join(path)}")
print(f"关系链: {' -> '.join(rels)}")


# 查找某人的所有直接联系人
print(f"张三的直接联系人: {list(G.successors('张三'))}")

# 查找某人的所有间接联系人（二度人脉）
def get_indirect_contacts(G, person, depth=2):
    return {n for n in nx.descendants_at_distance(G, person, depth)}

print(f"张三的二度人脉: {get_indirect_contacts(G, '张三', 2)}")