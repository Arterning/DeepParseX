#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from backend.app.admin.service.doc_service import sys_doc_service
from backend.app.admin.service.llm_service import llm_service
from backend.utils.doc_utils import request_text_to_vector



class ChatService:


    @staticmethod
    async def rag_chat(text: str, max_length = 512, check_topk = 10):

        question_text_emb = request_text_to_vector(text=text, max_length=max_length)
        query_vector = question_text_emb[0]["embs"]

        similar_docs = await sys_doc_service.search_chunk_vector(query_vector=query_vector, limit=check_topk)
        context = "\n".join([doc.chunk_text for doc in similar_docs if doc.chunk_text])
        system_context = (
            "上下文信息如下。\n"
            "---\n"
            f"{context}\n"
            "---\n"
            "请根据上下文信息而不是先验知识来回答以下的查询。并在回答中用 [编号] 标注引用的超链接来源。"
            "作为一个人工智能助手，你的回答要尽可能严谨。"
        )

        sources = {}  # 存储编号与超链接映射
        for idx, doc in enumerate(similar_docs):
            if doc.chunk_text:
                link = f"[{idx + 1}] <a href='/data/doc-detail/{doc.doc_id}'>{doc.doc_name}</a>"
                # 存储编号与超链接的映射
                sources[f"[{idx + 1}]"] = link

        
        response = await llm_service.get_llm_response(system_context, text)


        # 替换回答中的 [编号] 为超链接
        for ref, link in sources.items():
            response = response.replace(ref, f"{link}")

        # doc_dict = {}
        # for doc in similar_docs:
        #     doc_name = doc.doc_name
        #     if doc_name not in doc_dict:
        #         doc_dict[doc_name] = {"doc": doc, "distances": []}
        #     doc_dict[doc_name]["distances"].append(doc.distance)

        # unique_docs = []
        # for doc_name, data in doc_dict.items():
        #     doc = data["doc"]
        #     # 取平均 distance
        #     avg_distance = sum(data["distances"]) / len(data["distances"])
        #     if avg_distance < 1:
        #         unique_doc_dict = {
        #             "id": doc.id,
        #             "doc_id": doc.doc_id,
        #             "doc_name": doc.doc_name,
        #             "chunk_text": doc.chunk_text,
        #             "avg_distance": avg_distance
        #         }
        #         unique_docs.append(unique_doc_dict)
        
        # doc_list = "\n".join([
        # f"- <a href='/data/doc-detail/{doc['doc_id']}?type=doc'>{doc['doc_name']}</a> 相似度：{1 - doc['avg_distance']}"
        # for doc in unique_docs
        # if doc['doc_name'] and (1 - doc['avg_distance']) >= 0])
        # source = f"\n ## 找到{len(unique_docs)}个文件，数据来源：\n" if len(doc_list) > 0 else "\n ## 找到0个文件\n"
        # response += source
        # if len(doc_list) > 0:
        #     response += doc_list

        return response



chat_service = ChatService()
