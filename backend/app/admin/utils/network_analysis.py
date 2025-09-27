#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import networkx as nx
from collections import Counter


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
        eigenvector_centrality = nx.eigenvector_centrality(G)
        top_eigenvector = max(eigenvector_centrality, key=eigenvector_centrality.get)
        print(f"特征向量中心性最高: {top_eigenvector} ({eigenvector_centrality[top_eigenvector]:.3f})")
        eigenvector_result = eigenvector_centrality
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