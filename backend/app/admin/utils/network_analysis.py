#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import networkx as nx
from collections import Counter
from typing import List, Dict, Set, Tuple, Optional



# ============================================
# 辅助函数：颜色生成和混合
# ============================================

def generate_color(index, total):
    """生成区分度高的颜色"""
    # 使用HSL色彩空间生成颜色
    import colorsys
    
    hue = index / total
    saturation = 0.7
    lightness = 0.6
    
    r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation)
    
    return f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'


def analyze_node_degrees(G):
    """分析节点的度数（连接数量）"""
    print("=== 节点度数分析 ===")
    
    # 计算每个节点的度数
    degrees = dict(G.degree())
    
    # 找出度数最高的节点
    max_degree_node = max(degrees, key=degrees.get)
    max_degree = degrees[max_degree_node]
    
    print(f"连接最多的节点: {max_degree_node} (度数: {max_degree})")
    
    # 度数分布
    degree_sequence = sorted([d for n, d in G.degree()], reverse=True)
    print(f"度数序列: {degree_sequence}")
    
    # 度数统计
    degree_count = Counter(degrees.values())
    print(f"度数分布: {dict(degree_count)}")
    
    return degrees


def analyze_centrality(G):
    """分析各种中心性指标"""
    print("\n=== 中心性分析 ===")
    
    # 度中心性（Degree Centrality）
    degree_centrality = nx.degree_centrality(G)
    top_degree_central = max(degree_centrality, key=degree_centrality.get)
    print(f"度中心性最高: {top_degree_central} ({degree_centrality[top_degree_central]:.3f})")
    
    # 介数中心性（Betweenness Centrality）
    betweenness_centrality = nx.betweenness_centrality(G)
    top_betweenness = max(betweenness_centrality, key=betweenness_centrality.get)
    print(f"介数中心性最高: {top_betweenness} ({betweenness_centrality[top_betweenness]:.3f})")
    
    # 接近中心性（Closeness Centrality）
    closeness_centrality = nx.closeness_centrality(G)
    top_closeness = max(closeness_centrality, key=closeness_centrality.get)
    print(f"接近中心性最高: {top_closeness} ({closeness_centrality[top_closeness]:.3f})")
    
    # 特征向量中心性（Eigenvector Centrality）
    eigenvector_result = None
    try:
        # 对于有向图，尝试使用numpy实现的特征向量中心性或增加迭代次数
        if G.is_directed():
            print("使用katz中心性作为有向图的替代指标...")
            eigenvector_centrality = nx.katz_centrality(G)
        else:
            # 增加迭代次数和调整收敛容差
            eigenvector_centrality = nx.eigenvector_centrality(G, max_iter=500, tol=1e-05)
        
        top_eigenvector = max(eigenvector_centrality, key=eigenvector_centrality.get)
        print(f"特征向量中心性最高: {top_eigenvector} ({eigenvector_centrality[top_eigenvector]:.3f})")
        eigenvector_result = eigenvector_centrality
    except nx.PowerIterationFailedConvergence:
        print("特征向量中心性: 幂迭代未能收敛，尝试使用替代方法")
        try:
            # 尝试使用katz中心性作为替代
            eigenvector_centrality = nx.katz_centrality(G)
            top_eigenvector = max(eigenvector_centrality, key=eigenvector_centrality.get)
            print(f"Katz中心性最高: {top_eigenvector} ({eigenvector_centrality[top_eigenvector]:.3f})")
            eigenvector_result = eigenvector_centrality
        except Exception as e:
            print(f"特征向量中心性计算失败: {str(e)}")
    except nx.NetworkXError:
        print("特征向量中心性: 无法计算（可能是非连通图）")
    
    result = {
        'degree': degree_centrality,
        'betweenness': betweenness_centrality,
        'closeness': closeness_centrality
    }
    
    if eigenvector_result:
        result['eigenvector'] = eigenvector_result
    
    return result


def find_key_nodes(G):
    """寻找网络中的关键节点"""
    print("\n=== 关键节点识别 ===")
    
    # 度数最高的节点
    degrees = dict(G.degree())
    top_degree_nodes = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:3]
    print("度数最高的前3个节点:")
    for node, degree in top_degree_nodes:
        print(f"  {node}: {degree}")
    
    # 介数中心性最高的节点（桥梁节点）
    betweenness = nx.betweenness_centrality(G)
    top_betweenness_nodes = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:3]
    print("\n介数中心性最高的前3个节点（桥梁节点）:")
    for node, centrality in top_betweenness_nodes:
        print(f"  {node}: {centrality:.3f}")
    
    # 移除后对网络影响最大的节点
    print("\n移除节点对网络连通性的影响:")
    # 将有向图转换为无向图以计算连通组件
    G_undirected = G.to_undirected()
    original_components = nx.number_connected_components(G_undirected)
    
    # 只测试前5个节点
    top_nodes = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:5]
    impact_results = []
    
    for node, _ in top_nodes:  # 只测试前5个节点
        G_copy = G.copy()
        G_copy.remove_node(node)
        # 计算移除节点后的连通组件数量
        G_copy_undirected = G_copy.to_undirected()
        new_components = nx.number_connected_components(G_copy_undirected)
        impact = new_components - original_components
        impact_results.append({
            'node': node,
            'impact': impact
        })
        print(f"  移除 {node}: 连通组件变化 +{impact}")
    
    return {
        'top_degree_nodes': top_degree_nodes,
        'top_betweenness_nodes': top_betweenness_nodes,
        'node_impacts': impact_results
    }


def build_networkx_graph(nodes, edges):
    """从节点和边数据构建NetworkX图"""
    G = nx.DiGraph()
    
    # 添加节点
    for node in nodes:
        G.add_node(node['id'], **node)
    
    # 添加边
    for edge in edges:
        G.add_edge(edge['source'], edge['target'], **edge)
    
    return G



# ============================================
# 方案1: 硬划分社区（每个节点只属于一个社区）
# ============================================

def detect_communities_hard_partition(G):
    """
    检测社区（硬划分），每个节点只属于一个社区
    返回适合前端使用的数据结构
    """
    # 使用贪婪模块化算法
    communities = nx.community.greedy_modularity_communities(G)
    
    # 构建返回数据
    response = {
        'partition_type': 'hard',  # 硬划分
        'num_communities': len(communities),
        'modularity': nx.community.modularity(G, communities),
        'communities': [],
        'nodes': {},
        'edges': []
    }
    
    # 为每个社区分配ID和颜色
    for i, community in enumerate(communities):
        community_id = i + 1
        community_data = {
            'id': community_id,
            'size': len(community),
            'nodes': sorted(list(community)),
            'color': generate_color(i, len(communities))  # 生成颜色
        }
        response['communities'].append(community_data)
        
        # 为每个节点记录其社区信息
        for node in community:
            response['nodes'][node] = {
                'community_id': community_id,
                'color': community_data['color']
            }
    
    # 添加边信息（包括是否跨社区）
    for u, v in G.edges():
        edge_data = {
            'source': u,
            'target': v,
            'is_inter_community': response['nodes'][u]['community_id'] != response['nodes'][v]['community_id']
        }
        response['edges'].append(edge_data)
    
    return response


# ============================================
# 方案2: 重叠社区检测（节点可以属于多个社区）
# ============================================

def detect_communities_overlapping(G):
    """
    检测重叠社区，节点可以属于多个社区
    返回适合前端使用的数据结构
    """
    try:
        # 使用重叠社区检测算法（例如k-clique percolation）
        communities = list(nx.community.k_clique_communities(G, k=3))
    except:
        # 如果k-clique失败，降级使用硬划分
        return detect_communities_hard_partition(G)
    
    response = {
        'partition_type': 'overlapping',  # 重叠社区
        'num_communities': len(communities),
        'communities': [],
        'nodes': {},
        'edges': []
    }
    
    # 为每个社区分配ID和颜色
    community_colors = []
    for i, community in enumerate(communities):
        community_id = i + 1
        color = generate_color(i, len(communities))
        community_colors.append(color)
        
        community_data = {
            'id': community_id,
            'size': len(community),
            'nodes': sorted(list(community)),
            'color': color
        }
        response['communities'].append(community_data)
    
    # 为每个节点记录其所属的所有社区
    for node in G.nodes():
        node_communities = []
        node_colors = []
        
        for i, community in enumerate(communities):
            if node in community:
                node_communities.append(i + 1)
                node_colors.append(community_colors[i])
        
        response['nodes'][node] = {
            'community_ids': node_communities,  # 所有所属社区
            'colors': node_colors,  # 所有对应颜色
            'is_overlapping': len(node_communities) > 1,  # 是否重叠节点
            'display_color': blend_colors(node_colors) if len(node_colors) > 1 else node_colors[0]
        }
    
    # 添加边信息
    for u, v in G.edges():
        u_communities = set(response['nodes'][u]['community_ids'])
        v_communities = set(response['nodes'][v]['community_ids'])
        
        edge_data = {
            'source': u,
            'target': v,
            'shared_communities': list(u_communities & v_communities),
            'is_inter_community': len(u_communities & v_communities) == 0
        }
        response['edges'].append(edge_data)
    
    return response