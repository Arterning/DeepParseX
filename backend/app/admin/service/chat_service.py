#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
from backend.app.admin.schema.chat import ChatParam
from backend.app.admin.service.doc_service import sys_doc_service
from backend.app.admin.service.llm_service import llm_service
from backend.app.admin.service.mail_msg_service import mail_msg_service
from backend.app.admin.utils.text_processor import embed_text_chunks
from backend.database.db_pg import async_db_session
from backend.app.admin.model.mail_msg import MailMsg
from backend.app.admin.model.sys_chat_message import ChatMessage
from backend.app.admin.model.sys_chat_session import ChatSession
from sqlalchemy import select



class ChatService:

    # 根据以下文件内容生成一个简洁的摘要
    @staticmethod
    async def generate_summary(id: int):
        # 获取文档
        doc = await sys_doc_service.get(pk=id)
        if not doc.content:
            return ""

        # 字符限制阈值
        CONTENT_LENGTH_THRESHOLD = 5000

        # 检查文档内容长度
        if len(doc.content) <= CONTENT_LENGTH_THRESHOLD:
            # 内容未超限，直接生成摘要
            system_context = "你是一个专业的文档摘要生成器。请根据以下文件内容生成一个简洁的摘要。"
            question = (
                "请根据以下文件内容生成一个简洁的摘要：\n"
                "---\n"
                f"{doc.content}\n"
                "---\n"
                "作为一个人工智能助手，你的回答要尽可能严谨。"
            )
        else:
            # 内容超限，使用向量检索方式
            # 固定查询词
            summary_query = "请总结这个文档的核心内容、主要观点和关键信息"

            # 对查询词进行向量化
            question_text_emb = await embed_text_chunks(summary_query)
            query_vector = question_text_emb[0]["embs"]

            # 检索该文档的相关片段（限定doc_id）
            similar_docs = await sys_doc_service.search_similar_docs(
                query_vector=query_vector,
                limit=10,
                distance_threshold=1.2,
                doc_id=id
            )

            # 构建上下文
            context_list = []
            for idx, doc_chunk in enumerate(similar_docs):
                if doc_chunk.chunk_text:
                    context_list.append(f"片段{idx + 1}: {doc_chunk.chunk_text}")

            context = "\n\n".join(context_list)

            # 构建系统提示词
            if context:
                system_context = "你是一个专业的文档摘要生成器。请根据以下文档片段生成一个简洁、全面的摘要。"
                question = (
                    "请根据以下文档片段生成一个简洁、全面的摘要：\n"
                    "---\n"
                    f"{context}\n"
                    "---\n"
                    "作为一个人工智能助手，你的回答要尽可能严谨、准确，并综合所有片段的关键信息。"
                )
            else:
                # 如果没有检索到相关片段，使用文档的前N个字符
                system_context = "你是一个专业的文档摘要生成器。请根据以下文件内容生成一个简洁的摘要。"
                question = (
                    "请根据以下文件内容生成一个简洁的摘要：\n"
                    "---\n"
                    f"{doc.content[:CONTENT_LENGTH_THRESHOLD]}\n"
                    "---\n"
                    "作为一个人工智能助手，你的回答要尽可能严谨。"
                )

        response = await llm_service.get_llm_response(system_context, question)
        await sys_doc_service.base_update(pk=id, obj={
            'desc': response
        })
        return response


    @staticmethod
    async def generate_translation(id: int, target_language: str, text: str):

        if id:
            doc = await sys_doc_service.get(pk=id)
        
        original_text = text if text else doc.content

        system_context = f"你是一个专业的翻译助手。请将以下内容翻译成{target_language}。"
        question = (
            f"请将以下内容翻译成{target_language}：\n"
            "---\n"
            f"{original_text}\n"
            "---\n"
            "作为一个人工智能助手，你的翻译要尽可能准确、流畅。"
        )
        response = await llm_service.get_llm_response(system_context, question)
        await sys_doc_service.base_update(pk=id, obj={
            'translation': response
        })
        # 更新到对应的邮件表
        # 根据文档ID查找关联的邮件
        if id:
            async with async_db_session() as db:
                # 查询doc_id等于当前id的邮件记录
                mail_msg = await db.execute(
                    select(MailMsg).where(MailMsg.doc_id == id)
                )
                mail_msg_obj = mail_msg.scalars().first()
                if mail_msg_obj:
                    # 将response的第一行更新到zh_subject，其余部分更新到zh_content
                    if response:
                        lines = response.split('\n', 1)
                        zh_subject = lines[0].strip() if lines else ''
                        zh_content = lines[1].strip() if len(lines) > 1 else ''
                        
                        # 更新邮件记录
                        await mail_msg_service.base_update(
                            pk=mail_msg_obj.id, 
                            obj={
                                'zh_subject': zh_subject,
                                'zh_content': zh_content
                            }
                        )
        
        return response

    
    @staticmethod
    async def rag_chat(obj: ChatParam, max_length = 512, check_topk = 10):
        # 获取历史对话记录
        history_context = ""
        if obj.session_id:
            async with async_db_session() as db:
                # 查询该会话的所有历史消息（排除当前这条）
                result = await db.execute(
                    select(ChatMessage)
                    .where(ChatMessage.session_id == obj.session_id)
                    .order_by(ChatMessage.created_time.asc())
                )
                messages = result.scalars().all()

                # 格式化历史对话
                if messages:
                    history_lines = []
                    for msg in messages:
                        role = "用户" if msg.sender == "user" else "助手"
                        history_lines.append(f"{role}: {msg.content}")
                    history_context = "\n".join(history_lines)

        if obj.doc_id:
            # 如果指定了文档ID，则使用向量检索该文档的相关片段
            # 验证文档是否存在
            doc = await sys_doc_service.get(pk=obj.doc_id)
            if not doc:
                return {
                    "answer": "指定的文档不存在。",
                    "chunks": []
                }

            # 检查是否为数据文件类型
            data_file_types = ['.parquet', '.csv', '.xlsx', '.xls']
            if doc.file_suffix in data_file_types:
                # 使用数据分析方法
                analysis_result = await sys_doc_service.analyze_data_with_ai(
                    pk=obj.doc_id,
                    question=obj.question
                )

                # 检查是否有错误
                if "error" in analysis_result:
                    return {
                        "answer": f"数据分析失败：{analysis_result['error']}",
                        "chunks": []
                    }

                # 构建系统提示词，让LLM生成自然语言回答
                system_context_parts = []

                # 添加历史对话
                if history_context:
                    system_context_parts.append(
                        "## 对话历史\n"
                        f"{history_context}\n"
                    )

                # 添加数据分析结果
                system_context_parts.append(
                    "## 数据分析结果\n"
                    f"用户问题：{analysis_result['question']}\n"
                    f"执行的SQL查询：\n```sql\n{analysis_result['sql_query']}\n```\n\n"
                    f"查询结果（共{analysis_result['result']['row_count']}行）：\n"
                    f"列名：{', '.join(analysis_result['result']['columns'])}\n"
                )

                # 格式化查询结果数据
                if analysis_result['result']['data']:
                    import json
                    result_data_str = json.dumps(
                        analysis_result['result']['data'],
                        ensure_ascii=False,
                        indent=2
                    )
                    system_context_parts.append(f"数据内容：\n```json\n{result_data_str}\n```\n")

                # 添加指导说明
                system_context_parts.append(
                    "\n请基于以上数据分析结果，用自然语言回答用户的问题。"
                    "回答要求：\n"
                    "1. 清晰、准确地解读查询结果\n"
                    "2. 如果有数值统计，请明确说明\n"
                    "3. 必要时可以总结关键发现\n"
                    "4. 保持专业和严谨的态度\n"
                )

                system_context = "\n".join(system_context_parts)
                response = await llm_service.get_llm_response(system_context, obj.question)

                return {
                    "answer": response,
                    "chunks": [],
                    "data_analysis": {
                        "sql_query": analysis_result['sql_query'],
                        "result_count": analysis_result['result']['row_count']
                    }
                }

            # 对用户问题进行向量化
            question_text_emb = await embed_text_chunks(obj.question)
            query_vector = question_text_emb[0]["embs"]

            # 使用向量检索，限定 doc_id
            similar_docs = await sys_doc_service.search_similar_docs(
                query_vector=query_vector,
                limit=check_topk,
                distance_threshold=1.2,
                doc_id=obj.doc_id
            )

            context_list = []
            sources = {}  # 存储编号与超链接映射
            chunks = []  # 存储文本片段列表

            for idx, doc_chunk in enumerate(similar_docs):
                if doc_chunk.chunk_text:
                    # 构建超链接
                    link = f"[{idx + 1}] <doclink data-doc-id=\"{doc_chunk.doc_id}\" data-chunk-id=\"{doc_chunk.chunk_id}\" data-doc-name=\"{doc_chunk.doc_name}\" >{doc_chunk.doc_name}</doclink>"
                    # 存储编号与超链接的映射
                    sources[f"[{idx + 1}]"] = link
                    source_entry = f"来源：[{idx + 1}] \n内容: {doc_chunk.chunk_text}"
                    context_list.append(source_entry)

                    # 将 chunk 信息添加到列表中
                    chunks.append({
                        "chunk_id": doc_chunk.chunk_id,
                        "chunk_text": doc_chunk.chunk_text,
                        "doc_id": doc_chunk.doc_id,
                        "doc_name": doc_chunk.doc_name
                    })

            context = "\n".join(context_list)

            # 构建系统提示词
            system_context_parts = []

            # 添加历史对话
            if history_context:
                system_context_parts.append(
                    "## 对话历史\n"
                    f"{history_context}\n"
                )

            # 添加知识库上下文
            if context:
                system_context_parts.append(
                    "## 知识库上下文\n"
                    "---\n"
                    f"{context}\n"
                    "---\n"
                )

            # 添加指导说明
            if context:
                system_context_parts.append(
                    "请基于以上知识库上下文提供详细、深入的分析和回答。"
                    "如果知识库中有相关信息，请充分引用并展开说明，并在回答中用 [编号] 标注引用的来源；"
                    "如果知识库中没有相关信息，可以结合你自己的知识给出专业建议。"
                    "作为一个人工智能助手，你的回答要尽可能严谨、全面、有深度。"
                )
            else:
                system_context_parts.append(
                    "知识库中未找到相关上下文信息，请根据你自己的知识和专业能力提供详细、深入的分析和回答。"
                    "作为一个人工智能助手，你的回答要尽可能严谨、全面、有深度。"
                )

            system_context = "\n".join(system_context_parts)
            response = await llm_service.get_llm_response(system_context, obj.question)

            # 替换回答中的 [编号] 为超链接
            for ref, link in sources.items():
                if response:
                    response = response.replace(ref, f"{link}")

            return {
                "answer": response,
                "chunks": chunks
            }
        else:
            question_text_emb = await embed_text_chunks(obj.question)
            query_vector = question_text_emb[0]["embs"]
            # 使用距离阈值过滤不相关的结果（距离越小越相似，默认1.2）
            similar_docs = await sys_doc_service.search_similar_docs(
                query_vector=query_vector,
                limit=check_topk,
                distance_threshold=1.2  # 可根据实际效果调整，建议范围 0.8-1.5
            )

            context_list = []
            sources = {}  # 存储编号与超链接映射
            chunks = []  # 存储文本片段列表

            for idx, doc in enumerate(similar_docs):
                if doc.chunk_text:
                    # 构建超链接，使用 chunk_id 代替 chunk_text
                    link = f"[{idx + 1}] <doclink data-doc-id=\"{doc.doc_id}\" data-chunk-id=\"{doc.chunk_id}\" data-doc-name=\"{doc.doc_name}\" >{doc.doc_name}</doclink>"
                    # 存储编号与超链接的映射
                    sources[f"[{idx + 1}]"] = link
                    source_entry = f"来源：[{idx + 1}] \n内容: {doc.chunk_text}"
                    context_list.append(source_entry)

                    # 将 chunk 信息添加到列表中
                    chunks.append({
                        "chunk_id": doc.chunk_id,
                        "chunk_text": doc.chunk_text,
                        "doc_id": doc.doc_id,
                        "doc_name": doc.doc_name
                    })


            context = "\n".join(context_list)

            # 构建系统提示词
            system_context_parts = []

            # 添加历史对话
            if history_context:
                system_context_parts.append(
                    "## 对话历史\n"
                    f"{history_context}\n"
                )

            # 添加知识库上下文
            if context:
                system_context_parts.append(
                    "## 知识库上下文\n"
                    "---\n"
                    f"{context}\n"
                    "---\n"
                )

            # 添加指导说明
            if context:
                system_context_parts.append(
                    "请基于以上知识库上下文提供详细、深入的分析和回答。"
                    "如果知识库中有相关信息，请充分引用并展开说明，并在回答中用 [编号] 标注引用的来源；"
                    "如果知识库中没有相关信息，可以结合你自己的知识给出专业建议。"
                    "作为一个人工智能助手，你的回答要尽可能严谨、全面、有深度。"
                )
            else:
                system_context_parts.append(
                    "知识库中未找到相关上下文信息，请根据你自己的知识和专业能力提供详细、深入的分析和回答。"
                    "作为一个人工智能助手，你的回答要尽可能严谨、全面、有深度。"
                )

            system_context = "\n".join(system_context_parts)

            response = await llm_service.get_llm_response(system_context, obj.question)


            # 替换回答中的 [编号] 为超链接
            for ref, link in sources.items():
                if response:
                    response = response.replace(ref, f"{link}")

            return {
                "answer": response,
                "chunks": chunks
            }


chat_service = ChatService()
