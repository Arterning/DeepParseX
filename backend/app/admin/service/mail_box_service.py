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
    build_networkx_graph,
    detect_communities_hard_partition
)

from backend.app.admin.crud.crud_mail_box import mail_box_dao
from backend.app.admin.crud.crud_mail_msg import mail_msg_dao
from backend.app.admin.model.mail_box import MailBox
from backend.app.admin.model.mail_msg import MailMsg
from backend.app.admin.model.sys_entity import Entity
from backend.app.admin.model.sys_entity_doc import sys_entity_doc
from backend.app.admin.schema.mail_box import CreateMailBoxParam, UpdateMailBoxParam
from backend.common.exception import errors
from backend.database.db_pg import async_db_session
from sqlalchemy import Select, or_, and_, select, distinct


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
    ) -> dict:
        """
        分析邮箱之间的关系

        :param mailboxes: 邮箱地址列表
        :param start_time: 开始时间
        :param end_time: 结束时间
        :param max_layers: 最大分析层级，默认3层
        :return: 包含nodes和edges的图结构
        """
        async with async_db_session() as db:

            # 存储所有邮箱及其层级
            mailbox_layers = {}
            # 存储邮箱间的关系统计
            relationships = defaultdict(lambda: {
                'send_count': 0,
                'reply_count': 0,
                'cc_count': 0,
                'first_interaction_time': None,
                'latest_time': None,
                'emails': [],
                'attachment_count': 0,
                'interaction_duration': 0,
                'description': ''
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
                        if related_email and related_email not in mailbox_layers:
                            # 即使不在下一层扩展，也要先添加到mailbox_layers中确保能被包含在结果中
                            mailbox_layers[related_email] = layer + 1
                            # 只有当还有下一层需要处理时，才添加到next_layer_emails
                            if layer < max_layers - 1:
                                next_layer_emails.add(related_email)

                    # 统计关系 - 发送关系（发送者到每个收件人）
                    if email_obj.sender and receiver_list:
                        for receiver in receiver_list:
                            if receiver:
                                key = (email_obj.sender, receiver, 'send')
                                # 判断是否为回复邮件（标题包含RE:）
                                if hasattr(email_obj, 'name') and email_obj.name and isinstance(email_obj.name, str) and 'RE:' in email_obj.name.upper():
                                    relationships[key]['reply_count'] += 1
                                else:
                                    relationships[key]['send_count'] += 1
                                relationships[key]['emails'].append(email_obj)
                                relationships[key]['attachment_count'] += len(email_obj.attachments)
                                if not relationships[key]['first_interaction_time'] or email_obj.time < relationships[key]['first_interaction_time']:
                                    relationships[key]['first_interaction_time'] = email_obj.time
                                if not relationships[key]['latest_time'] or email_obj.time > relationships[key]['latest_time']:
                                    relationships[key]['latest_time'] = email_obj.time

                    # 统计关系 - 抄送关系（发送者到每个抄送人）
                    if email_obj.sender and cc_list:
                        for cc_email in cc_list:
                            if cc_email:
                                key = (email_obj.sender, cc_email, 'cc')
                                # 判断是否为回复邮件（标题包含RE:）
                                if hasattr(email_obj, 'name') and email_obj.name and isinstance(email_obj.name, str) and 'RE:' in email_obj.name.upper():
                                    relationships[key]['reply_count'] += 1
                                else:
                                    relationships[key]['cc_count'] += 1
                                relationships[key]['emails'].append(email_obj)
                                relationships[key]['attachment_count'] += len(email_obj.attachments)
                                if not relationships[key]['first_interaction_time'] or email_obj.time < relationships[key]['first_interaction_time']:
                                    relationships[key]['first_interaction_time'] = email_obj.time
                                if not relationships[key]['latest_time'] or email_obj.time > relationships[key]['latest_time']:
                                    relationships[key]['latest_time'] = email_obj.time

                current_layer_emails = next_layer_emails

            # 计算权重并构建图结构
            nodes = []
            edges = []

            # 确保只返回不超过max_layers层级的邮箱节点
            all_emails_to_include = set()
            for email, layer in mailbox_layers.items():
                # 只包含层级小于等于max_layers的邮箱，同时确保输入的所有邮箱都被包含
                if layer <= max_layers or email in mailboxes:
                    all_emails_to_include.add(email)

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
                    # 计算关系权重
                    weight = 0
                    
                    # 关系权重 = （发送次数 × 0.4） + （回复次数 × 0.3） + （含个人文件附件次数 × 0.2） + （互动持续时间 × 0.1）
                    send_count = data.get('send_count', 0)
                    reply_count = data.get('reply_count', 0)
                    attachment_count = data.get('attachment_count', 0)
                    if data.get('first_interaction_time') and data.get('latest_time'):
                        # 计算天数差，如果在同一天则为1天
                        start_time = data.get('first_interaction_time')
                        end_time = data.get('latest_time')
                        if start_time.date() == end_time.date():
                            interaction_duration = 1
                        else:
                            # 计算完整天数
                            interaction_duration = (end_time - start_time).days + 1
                    else:
                        interaction_duration = 0
                    data['interaction_duration'] = interaction_duration
                    data['description'] = f'发送次数: {send_count}, 回复次数: {reply_count}, 含个人文件附件次数: {attachment_count}, 互动持续时间: {int(interaction_duration)}天'

                    # 计算总权重
                    weight = (send_count * 0.4) + (reply_count * 0.3) + (attachment_count * 0.2) + (interaction_duration * 0.1)
                    
                    # 抄送关系权重降低50%
                    if relation_type == 'cc':
                        weight *= 0.5

                    # 密送关系权重增加50%
                    if relation_type == 'bcc':
                        weight *= 1.5

                    # 只添加有关系的边（权重可能为0但只要有数据就显示关系）
                    if any(data.get(key, 0) > 0 for key in ['send_count', 'reply_count', 'attachment_count', 'interaction_duration']):
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
                            'description': data['description'],
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
            communities_results = detect_communities_hard_partition(G)

            mailbox_mail_count = defaultdict(int)
            for edge in edges:
                source = edge['source']
                target = edge['target']
                interaction_count = edge['email_count']
                mailbox_mail_count[source] += interaction_count
                mailbox_mail_count[target] += interaction_count
            
            mail_count = dict(mailbox_mail_count)

            # 将分析结果添加到返回数据中
            result = {
                'nodes': nodes,
                'edges': edges,
                'network_analysis': {
                    'degrees': degrees,
                    'centrality': centrality_results,
                    'key_nodes': key_nodes_results,
                    'communities': communities_results,
                    'is_directed': G.is_directed(),
                    'number_of_nodes': G.number_of_nodes(),
                    'number_of_edges': G.number_of_edges(),
                    'number_of_connected_components': nx.number_connected_components(G.to_undirected()),
                    'mail_count': mail_count
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
        统计系统所有邮箱账号的类型（服务商）分布占比

        使用 SQL GROUP BY 按域名分组统计，再将已知域名映射为服务商名称

        :param start_time: 开始时间（保留参数兼容）
        :param end_time: 结束时间（保留参数兼容）
        :return: 包含邮箱类型和对应账号数量的列表
        """
        from sqlalchemy import func, text

        # 已知域名 -> 服务商映射
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
            'foxmail.com': 'Foxmail',
            'dnc.org': 'DNC',
            'rnc.org': 'RNC',
        }

        async with async_db_session() as db:
            # PostgreSQL split_part 按 @ 取域名，GROUP BY 统计
            domain_expr = func.lower(func.split_part(MailBox.name, '@', 2))
            query = (
                select(domain_expr.label('domain'), func.count().label('cnt'))
                .where(MailBox.name.contains('@'))
                .group_by(text('1'))
                .order_by(text('cnt DESC'))
            )
            result = await db.execute(query)
            rows = result.all()

            # 将已知域名映射为服务商名称，未知的直接用域名
            provider_count = defaultdict(int)
            for domain, cnt in rows:
                provider = major_providers.get(domain, domain)
                provider_count[provider] += cnt

            distribution = [
                {'name': provider, 'value': count}
                for provider, count in provider_count.items()
            ]
            distribution.sort(key=lambda x: x['value'], reverse=True)
            return distribution

    @staticmethod
    async def get_mailbox_detail_with_emails(*, pk: int) -> dict:
        """
        获取邮箱详情，包括发送/接收/抄送的邮件列表和相关人物实体

        :param pk: 邮箱ID
        :return: 包含邮箱信息、邮件列表和人物实体的字典
        """
        async with async_db_session() as db:
            # 获取邮箱信息
            mail_box = await mail_box_dao.get(db, pk)
            if not mail_box:
                raise errors.NotFoundError(msg='邮箱不存在')

            email = mail_box.name  # 邮箱地址

            # 查询发送者是这个邮箱的邮件
            sent_query = select(MailMsg).where(MailMsg.sender == email)
            sent_result = await db.execute(sent_query)
            sent_emails = sent_result.scalars().all()

            # 查询接收者包含这个邮箱的邮件
            received_query = select(MailMsg).where(MailMsg.receiver.like(f'%{email}%'))
            received_result = await db.execute(received_query)
            received_emails = received_result.scalars().all()

            # 查询抄送者包含这个邮箱的邮件
            cc_query = select(MailMsg).where(MailMsg.cc.like(f'%{email}%'))
            cc_result = await db.execute(cc_query)
            cc_emails = cc_result.scalars().all()

            # 收集所有邮件的doc_id
            all_doc_ids = set()
            for email_obj in sent_emails + received_emails + cc_emails:
                if email_obj.doc_id:
                    all_doc_ids.add(email_obj.doc_id)

            # 查询与这些文档相关的人物实体
            person_entities = []
            if all_doc_ids:
                # 先查询去重的实体ID，避免 DISTINCT 无法处理 JSON 列的问题
                entity_ids_query = (
                    select(distinct(sys_entity_doc.c.entity_id))
                    .join(Entity, Entity.id == sys_entity_doc.c.entity_id)
                    .where(
                        sys_entity_doc.c.doc_id.in_(all_doc_ids),
                        Entity.entity_type == '人物'
                    )
                )
                entity_ids_result = await db.execute(entity_ids_query)
                entity_ids = [row[0] for row in entity_ids_result.fetchall()]

                # 再根据ID查询完整的实体信息
                if entity_ids:
                    entity_query = select(Entity).where(Entity.id.in_(entity_ids))
                    entity_result = await db.execute(entity_query)
                    person_entities = entity_result.scalars().all()

            return {
                'mail_box': mail_box,
                'sent_emails': sent_emails,
                'received_emails': received_emails,
                'cc_emails': cc_emails,
                'person_entities': person_entities
            }


mail_box_service = MailBoxService()