#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import networkx as nx
from typing import Sequence
from datetime import datetime, timedelta
from collections import defaultdict, deque

from backend.app.admin.utils.network_analysis import (
    analyze_node_degrees,
    analyze_centrality,
    find_key_nodes,
    build_networkx_graph
)

from backend.app.admin.crud.crud_mail_box import mail_box_dao
from backend.app.admin.crud.crud_mail_msg import mail_msg_dao
from backend.app.admin.model.mail_box import MailBox
from backend.app.admin.model.mail_msg import MailMsg
from backend.app.admin.schema.mail_box import CreateMailBoxParam, UpdateMailBoxParam
from backend.common.exception import errors
from backend.database.db_pg import async_db_session
from sqlalchemy import Select, or_, and_, select


class MailBoxService:
    @staticmethod
    async def get(*, pk: int) -> MailBox:
        async with async_db_session() as db:
            mail_box = await mail_box_dao.get(db, pk)
            if not mail_box:
                raise errors.NotFoundError(msg='不存在')
            return mail_box
    
    @staticmethod
    async def get_select(*, name: str) -> Select:
        return await mail_box_dao.get_list(name=name)

    @staticmethod
    async def get_all() -> Sequence[MailBox]:
        async with async_db_session() as db:
            mail_boxs = await mail_box_dao.get_all(db)
            return mail_boxs

    @staticmethod
    async def get_by_name(*, name) -> None:
        async with async_db_session.begin() as db:
            return await mail_box_dao.get_by_name(db, name)
            

    @staticmethod
    async def create(*, obj: CreateMailBoxParam) -> None:
        async with async_db_session.begin() as db:
            found = await mail_box_dao.get_by_name(db, obj.name)
            if found:
                return
            await mail_box_dao.create(db, obj)

    @staticmethod
    async def update(*, pk: int, obj: UpdateMailBoxParam) -> int:
        async with async_db_session.begin() as db:
            count = await mail_box_dao.update(db, pk, obj)
            return count

    @staticmethod
    async def base_update(pk: int, obj: dict) -> int:
        async with async_db_session.begin() as db:
            count = await mail_box_dao.base_update(db, pk, obj)
            return count

    @staticmethod
    async def delete(*, pk: list[int]) -> int:
        async with async_db_session.begin() as db:
            count = await mail_box_dao.delete(db, pk)
            return count

    @staticmethod
    async def analyze_mailbox_relationships(
        *,
        mailboxes: list[str],
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        max_layers: int = 3,
        reference_time: datetime | None = None
    ) -> dict:
        """
        分析邮箱之间的关系

        :param mailboxes: 邮箱地址列表
        :param start_time: 开始时间
        :param end_time: 结束时间
        :param max_layers: 最大分析层级，默认3层
        :param reference_time: 时间权重计算的基准时间，默认为查询时间
        :return: 包含nodes和edges的图结构
        """
        async with async_db_session() as db:
            if reference_time is None:
                reference_time = datetime.now()

            # 存储所有邮箱及其层级
            mailbox_layers = {}
            # 存储邮箱间的关系统计
            relationships = defaultdict(lambda: {
                'send_count': 0,
                'receive_count': 0,
                'cc_count': 0,
                'latest_time': None,
                'emails': []
            })

            # 初始化起始邮箱为第0层
            for email in mailboxes:
                mailbox_layers[email] = 0

            # 按层级扩展邮箱关系
            current_layer_emails = set(mailboxes)
            processed_email_ids = set()  # 跨层去重，避免同一封邮件被重复统计

            for layer in range(max_layers):
                if not current_layer_emails:
                    break

                # 构建查询条件
                time_conditions = []
                if start_time:
                    time_conditions.append(MailMsg.time >= start_time)
                if end_time:
                    time_conditions.append(MailMsg.time <= end_time)

                # 查询当前层级邮箱相关的所有邮件
                query_conditions = []
                for email in current_layer_emails:
                    query_conditions.extend([
                        MailMsg.sender == email,
                        MailMsg.receiver.like(f'%{email}%'),
                        MailMsg.cc.like(f'%{email}%')
                    ])

                query = select(MailMsg).where(or_(*query_conditions))
                if time_conditions:
                    query = query.where(and_(*time_conditions))

                result = await db.execute(query)
                emails = result.scalars().all()

                # 处理查询到的邮件
                next_layer_emails = set()
                for email_obj in emails:
                    # 跳过已处理的邮件，避免重复统计关系
                    if email_obj.id in processed_email_ids:
                        continue
                    processed_email_ids.add(email_obj.id)
                    # 解析收件人列表（可能有多个，逗号分隔）
                    receiver_list = [r.strip() for r in email_obj.receiver.split(',') if r.strip()] if email_obj.receiver else []

                    # 解析抄送列表（可能有多个，逗号分隔）
                    cc_list = [cc.strip() for cc in email_obj.cc.split(',') if cc.strip()] if email_obj.cc else []

                    # 收集所有相关邮箱
                    all_related_emails = []
                    if email_obj.sender:
                        all_related_emails.append(email_obj.sender)
                    all_related_emails.extend(receiver_list)
                    all_related_emails.extend(cc_list)

                    # 为下一层收集新的邮箱
                    for related_email in all_related_emails:
                        if related_email and related_email not in mailbox_layers and layer < max_layers - 1:
                            mailbox_layers[related_email] = layer + 1
                            next_layer_emails.add(related_email)

                    # 统计关系 - 发送关系（发送者到每个收件人）
                    if email_obj.sender and receiver_list:
                        for receiver in receiver_list:
                            if receiver:
                                key = (email_obj.sender, receiver, 'send')
                                relationships[key]['send_count'] += 1
                                relationships[key]['emails'].append(email_obj)
                                if not relationships[key]['latest_time'] or email_obj.time > relationships[key]['latest_time']:
                                    relationships[key]['latest_time'] = email_obj.time

                    # 统计关系 - 抄送关系（发送者到每个抄送人）
                    if email_obj.sender and cc_list:
                        for cc_email in cc_list:
                            if cc_email:
                                key = (email_obj.sender, cc_email, 'cc')
                                relationships[key]['cc_count'] += 1
                                relationships[key]['emails'].append(email_obj)
                                if not relationships[key]['latest_time'] or email_obj.time > relationships[key]['latest_time']:
                                    relationships[key]['latest_time'] = email_obj.time

                current_layer_emails = next_layer_emails

            # 计算权重并构建图结构
            nodes = []
            edges = []

            # 确保输入的所有邮箱都作为节点返回，即使没有邮件记录
            all_emails_to_include = set(mailboxes) | set(mailbox_layers.keys())

            # 构建节点
            for email in all_emails_to_include:
                layer = mailbox_layers.get(email, 0)  # 输入的邮箱如果没有关系也设为0层

                # 统计该邮箱的总邮件数（去重）并构建邮件详细信息列表
                unique_emails = set()
                node_emails = []
                seen_email_ids = set()

                for key, data in relationships.items():
                    if key[0] == email or key[1] == email:
                        for email_obj in data['emails']:
                            unique_emails.add(email_obj.id)
                            # 为节点构建去重的邮件详细信息列表
                            if email_obj.id not in seen_email_ids:
                                seen_email_ids.add(email_obj.id)
                                node_emails.append({
                                    'id': email_obj.id,
                                    'subject': email_obj.subject,
                                    'time': email_obj.time.isoformat() if email_obj.time else None
                                })

                email_count = len(unique_emails)

                nodes.append({
                    'id': email,
                    'label': email,
                    'email_count': email_count,
                    'layer': layer,
                    'emails': node_emails
                })

            # 构建边
            for (source, target, relation_type), data in relationships.items():
                if source in all_emails_to_include and target in all_emails_to_include:
                    # 计算时间衰减权重
                    weight = 0
                    email_count = 0

                    if relation_type == 'send':
                        email_count = data['send_count']
                    elif relation_type == 'cc':
                        email_count = data['cc_count']

                    # 计算权重
                    if email_count > 0:
                        if data['latest_time']:
                            # 线性时间衰减：越近的时间权重越高
                            days_diff = (reference_time - data['latest_time']).days
                            time_weight = max(0, 1 - days_diff / 365)  # 一年后权重降为0
                        else:
                            # 如果没有时间信息，给一个默认权重
                            time_weight = 0.5

                        # 抄送关系权重降低50%
                        base_weight = email_count * time_weight
                        if relation_type == 'cc':
                            base_weight *= 0.5

                        weight = base_weight

                    # 只添加有邮件数量的边（即使权重为0也要显示关系）
                    if email_count > 0:
                        # 构建该边对应的邮件详细信息列表（去重）
                        edge_emails = []
                        seen_email_ids = set()
                        for email_obj in data['emails']:
                            if email_obj.id not in seen_email_ids:
                                seen_email_ids.add(email_obj.id)
                                edge_emails.append({
                                    'id': email_obj.id,
                                    'subject': email_obj.subject,
                                    'time': email_obj.time.isoformat() if email_obj.time else None
                                })

                        edges.append({
                            'source': source,
                            'target': target,
                            'weight': round(weight, 2),
                            'email_count': email_count,
                            'latest_time': data['latest_time'].isoformat() if data['latest_time'] else None,
                            'relation_type': relation_type,
                            'emails': edge_emails
                        })

            # 构建NetworkX图并进行网络分析
            G = build_networkx_graph(nodes, edges)
            
            # 执行各种网络分析
            degrees = analyze_node_degrees(G)
            centrality_results = analyze_centrality(G)
            key_nodes_results = find_key_nodes(G)
            
            # 将分析结果添加到返回数据中
            result = {
                'nodes': nodes,
                'edges': edges,
                'network_analysis': {
                    'degrees': degrees,
                    'centrality': centrality_results,
                    'key_nodes': key_nodes_results,
                    'is_directed': G.is_directed(),
                    'number_of_nodes': G.number_of_nodes(),
                    'number_of_edges': G.number_of_edges(),
                    'number_of_connected_components': nx.number_connected_components(G.to_undirected())
                }
            }
            
            return result


    @staticmethod
    async def get_mailbox_ranking(
        *, 
        top_n: int = 10,
        start_time: datetime | None = None,
        end_time: datetime | None = None
    ) -> list[dict]:
        """
        获取邮件数量排名前N的邮箱
        
        :param top_n: 返回前N个邮箱，默认10个
        :param start_time: 开始时间
        :param end_time: 结束时间
        :return: 包含邮箱和对应邮件数量的列表
        """
        async with async_db_session() as db:
            # 构建查询条件
            time_conditions = []
            if start_time:
                time_conditions.append(MailMsg.time >= start_time)
            if end_time:
                time_conditions.append(MailMsg.time <= end_time)
            
            # 统计每个邮箱参与的邮件数量（去重）
            mailbox_count = defaultdict(set)
            
            # 查询条件
            query = select(MailMsg)
            if time_conditions:
                query = query.where(and_(*time_conditions))
            
            result = await db.execute(query)
            emails = result.scalars().all()
            
            # 统计每个邮箱参与的邮件数量
            for email_obj in emails:
                # 处理发件人
                if email_obj.sender:
                    mailbox_count[email_obj.sender].add(email_obj.id)
                
                # 处理收件人
                if email_obj.receiver:
                    receivers = [r.strip() for r in email_obj.receiver.split(',') if r.strip()]
                    for receiver in receivers:
                        mailbox_count[receiver].add(email_obj.id)
                
                # 处理抄送人
                if email_obj.cc:
                    ccs = [cc.strip() for cc in email_obj.cc.split(',') if cc.strip()]
                    for cc in ccs:
                        mailbox_count[cc].add(email_obj.id)
            
            # 转换为列表并按邮件数量排序
            ranking = []
            for email, email_ids in mailbox_count.items():
                ranking.append({
                    'email': email,
                    'count': len(email_ids)
                })
            
            # 按邮件数量降序排序并返回前N个
            ranking.sort(key=lambda x: x['count'], reverse=True)
            return ranking[:top_n]
    
    @staticmethod
    async def get_email_provider_distribution(
        *, 
        start_time: datetime | None = None,
        end_time: datetime | None = None
    ) -> list[dict]:
        """
        统计邮箱类型分布
        
        :param start_time: 开始时间
        :param end_time: 结束时间
        :return: 包含邮箱类型和对应数量的列表
        """
        async with async_db_session() as db:
            # 构建查询条件
            time_conditions = []
            if start_time:
                time_conditions.append(MailMsg.time >= start_time)
            if end_time:
                time_conditions.append(MailMsg.time <= end_time)
            
            # 定义主要邮箱服务商
            major_providers = {
                'gmail.com': 'Gmail',
                'outlook.com': 'Outlook',
                'hotmail.com': 'Outlook',
                'live.com': 'Outlook',
                'protonmail.com': 'Proton',
                'proton.me': 'Proton',
                'qq.com': 'QQ',
                '163.com': '网易',
                '126.com': '网易',
                'yeah.net': '网易',
                'sina.com': '新浪',
                'sohu.com': '搜狐',
                'aliyun.com': '阿里云',
                'foxmail.com': 'Foxmail'
            }
            
            # 统计邮箱服务商分布
            provider_count = defaultdict(set)
            
            # 查询条件
            query = select(MailMsg)
            if time_conditions:
                query = query.where(and_(*time_conditions))
            
            result = await db.execute(query)
            emails = result.scalars().all()
            
            # 统计邮箱服务商分布
            for email_obj in emails:
                # 获取所有涉及的邮箱
                all_emails = set()
                
                # 处理发件人
                if email_obj.sender:
                    all_emails.add(email_obj.sender)
                
                # 处理收件人
                if email_obj.receiver:
                    receivers = [r.strip() for r in email_obj.receiver.split(',') if r.strip()]
                    all_emails.update(receivers)
                
                # 处理抄送人
                if email_obj.cc:
                    ccs = [cc.strip() for cc in email_obj.cc.split(',') if cc.strip()]
                    all_emails.update(ccs)
                
                # 统计每个邮箱的服务商
                for email in all_emails:
                    try:
                        # 提取域名
                        domain = email.split('@')[1].lower()
                        # 检查是否为主要服务商
                        provider = 'Other'
                        for key, value in major_providers.items():
                            if key in domain:
                                provider = value
                                break
                        # 记录该邮件涉及的服务商
                        provider_count[provider].add(email_obj.id)
                    except (IndexError, AttributeError):
                        # 忽略无效邮箱格式
                        continue
            
            # 转换为列表并按数量排序
            distribution = []
            for provider, email_ids in provider_count.items():
                distribution.append({
                    'name': provider,
                    'value': len(email_ids)
                })
            
            # 按数量降序排序
            distribution.sort(key=lambda x: x['value'], reverse=True)
            return distribution

mail_box_service = MailBoxService()