#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
from backend.app.admin.schema.chat import ChatParam
from backend.app.admin.service.doc_service import sys_doc_service
from backend.app.admin.service.llm_service import llm_service
from backend.utils.doc_utils import request_text_to_vector



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
        else:
            loop = asyncio.get_event_loop()
            question_text_emb = await loop.run_in_executor(None, request_text_to_vector, obj.question)
            query_vector = question_text_emb[0]["embs"]
            similar_docs = await sys_doc_service.search_chunk_vector(query_vector=query_vector, limit=check_topk)
            context = "\n".join([doc.chunk_text for doc in similar_docs if doc.chunk_text])
            system_context = (
                "上下文信息如下。\n"
                "---\n"
                f"{context}\n"
                "---\n"
                "请根据上下文信息而不是先验知识来回答以下的查询。并在回答中用 [编号] 标注引用的来源。"
                "作为一个人工智能助手，你的回答要尽可能严谨。"
            )

            sources = {}  # 存储编号与超链接映射
            for idx, doc in enumerate(similar_docs):
                if doc.chunk_text:
                    # 对chunk_text进行HTML转义，防止特殊字符影响属性值
                    escaped_chunk_text = doc.chunk_text.replace('"', '&quot;').replace("'", '&#39;')
                    link = f"[{idx + 1}] <a href=\"javascript:void(0)\" data-doc-id=\"{doc.doc_id}\" data-chunk-text=\"{escaped_chunk_text}\" data-doc-name=\"{doc.doc_name}\" onclick=\"openDrawer(this)\">{doc.doc_name}</a>"
                    # 存储编号与超链接的映射
                    sources[f"[{idx + 1}]"] = link

        
            response = await llm_service.get_llm_response(system_context, obj.question)


            # 替换回答中的 [编号] 为超链接
            for ref, link in sources.items():
                response = response.replace(ref, f"{link}")

        return response


chat_service = ChatService()
