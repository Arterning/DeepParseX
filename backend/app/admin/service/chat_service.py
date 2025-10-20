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
from sqlalchemy import select



class ChatService:

    # 根据以下文件内容生成一个简洁的摘要
    @staticmethod
    async def generate_summary(id: int):
        # 获取文档
        doc = await sys_doc_service.get(pk=id)
        if not doc.content:
            return ""
        system_context = "你是一个专业的文档摘要生成器。请根据以下文件内容生成一个简洁的摘要。"
        question = (
            "请根据以下文件内容生成一个简洁的摘要：\n"
            "---\n"
            f"{doc.content}\n"
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

        if obj.doc_id:
            # 如果指定了文档ID，则只查询该文档的相关片段
            doc = await sys_doc_service.get(pk=obj.doc_id)
            if not doc:
                return "指定的文档不存在。"
            context = doc.content if doc.content else ""
            system_context = (
                "上下文信息如下。\n"
                "---\n"
                f"{context}\n"
                "---\n"
                "请根据上下文信息而不是先验知识来回答以下的查询。"
                "作为一个人工智能助手，你的回答要尽可能严谨。"
            )
            response = await llm_service.get_llm_response(system_context, obj.question)
            # 异步调用insert_text_embs，不等待返回
            asyncio.create_task(sys_doc_service.compute_embedding(id=obj.doc_id))
        else:
            loop = asyncio.get_event_loop()
            question_text_emb = await loop.run_in_executor(None, embed_text_chunks, obj.question)
            query_vector = question_text_emb[0]["embs"]
            similar_docs = await sys_doc_service.search_similar_docs(query_vector=query_vector, limit=check_topk)
            
            context_list = []
            sources = {}  # 存储编号与超链接映射
            for idx, doc in enumerate(similar_docs):
                if doc.chunk_text:
                    # 对chunk_text进行HTML转义，防止特殊字符影响属性值
                    escaped_chunk_text = doc.chunk_text.replace('"', '&quot;').replace("'", '&#39;')
                    link = f"[{idx + 1}] <a href=\"javascript:void(0)\" data-doc-id=\"{doc.doc_id}\" data-chunk-text=\"{escaped_chunk_text}\" data-doc-name=\"{doc.doc_name}\" onclick=\"openDrawer(this)\">{doc.doc_name}</a>"
                    # 存储编号与超链接的映射
                    sources[f"[{idx + 1}]"] = link
                    source_entry = f"来源：[{idx + 1}] \n内容: {doc.chunk_text}"
                    context_list.append(source_entry)

                    
            context = "\n".join(context_list)

            system_context = (
                "上下文信息如下。\n"
                "---\n"
                f"{context}\n"
                "---\n"
                "请根据上下文信息而不是先验知识来回答以下的查询。并在回答中用 [编号] 标注引用的来源。"
                "作为一个人工智能助手，你的回答要尽可能严谨。"
            )

        
            response = await llm_service.get_llm_response(system_context, obj.question)


            # 替换回答中的 [编号] 为超链接
            for ref, link in sources.items():
                response = response.replace(ref, f"{link}")

        return response


chat_service = ChatService()
