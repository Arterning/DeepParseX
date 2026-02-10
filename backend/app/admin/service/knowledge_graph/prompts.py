"""Centralized repository for all LLM prompts used in the knowledge graph system."""

# Phase 1: Main extraction prompts
MAIN_SYSTEM_PROMPT = """
你是一个高级人工智能系统，专注于知识提取和知识图谱生成。
你的专长包括识别文本中一致的实体引用和有意义的关系。
重要说明：所有关系（谓词）的长度不得超过 3 个词。理想情况下，1-2 个词。这是一个硬性限制。
"""

MAIN_USER_PROMPT = """
任务：读取以下文本（```分隔），提取所有主语-谓语-宾语（S-P-O）三元组，生成JSON数组（仅含三元组对象，无其他文本）。

规则（必遵）：
1. 实体类型：人物（具体人名，如"张三"、"Elon Musk"）、组织（具体组织名，如"谷歌"、"清华大学"）、地点（城市/国家/建筑）、事件（具体事件名，如"2024世界人工智能大会"）、邮箱（完整地址）；
   - 所有实体必须是文本中提到的具体、可指代现实世界唯一对象的命名实体；
   - 严禁将抽象角色、职业、身份、泛称概念作为实体（如"咨询顾问"、"开源开发者"、"推广人才"、"著者"、"科技公司"、"行业峰会"等均不是有效实体）；
2. 实体统一：同实体用完整名（如"John Smith"替代"John"），缩写转全称（如"AI"→"人工智能"），代词替换为实体（如"他"→"张三"）；
3. 谓词限制：1-3个字，简洁（如"创立"、"位于"、"参加"）；
4. 三元组要求：句子内/短段落内有意义的关系需全覆盖，S/P/O均小写；
5. 原子性：实体不合并（如"北京故宫"是1个地点，不拆分为"北京"+"故宫"）。

输出格式（仅JSON，无注释）：
[
  {"subject": "实体1", "predicate": "谓词", "object": "实体2"},
  ...
]

待分析文本：
"""

# Phase 2: Entity standardization prompts
ENTITY_RESOLUTION_SYSTEM_PROMPT = """
你是实体解析和知识表示方面的专家。
你的任务是标准化知识图谱中的实体名称，以确保一致性。
"""

def get_entity_resolution_user_prompt(entity_list):
    return f"""
以下是从知识图谱中提取的实体名称列表。
有些实体名称可能指代相同的现实世界实体，但措辞不同。

请识别指代同一概念的实体组，并为每组提供标准化名称。
请以 JSON 对象的形式返回您的答案，其中键是标准化名称，值是所有应映射到该标准名称的变体名称的数组。
仅包含具有多个变体或需要标准化的实体。

实体列表：
{entity_list}

将您的响应格式化为有效的 JSON，如下所示：
{{
  "standardized name 1": ["variant 1", "variant 2"],
  "standardized name 2": ["variant 3", "variant 4", "variant 5"]
}}
"""

# Phase 3: Community relationship inference prompts
RELATIONSHIP_INFERENCE_SYSTEM_PROMPT = """
你是知识表示和推理方面的专家。
你的任务是推断知识图谱中不相关实体之间的合理关系。
"""

def get_relationship_inference_user_prompt(entities1, entities2, triples_text):
    return f"""
我有一个知识图谱，其中包含两个互不关联的实体社群。

社群 1 的实体：{entities1}
社群 2 的实体：{entities2}

以下是涉及这些实体的一些现有关系：
{triples_text}

请推断社群 1 中的实体与社群 2 中的实体之间 2-3 种可能的关联关系。
请以以下格式的 JSON 三元组数组形式返回您的答案：

[
    {{
    "subject": "来自社群 1 的实体",
    "predicate": "推断的关系",
    "object": "来自社群 2 的实体"
    }},
...
]

请仅包含具有明确谓词且高度合理的关联关系。
重要提示：推断的关系（谓词）不得超过 3 个词。最好是 1-2 个词。切勿超过 3 个词。
对于谓词，请使用能够清晰描述关系的短语。
重要提示：确保主体和客体是不同的实体 - 避免自我引用。
"""

# Phase 4: Within-community relationship inference prompts
WITHIN_COMMUNITY_INFERENCE_SYSTEM_PROMPT = """
你是知识表示和推理方面的专家。
你的任务是推断知识图谱中尚未连接的语义相关实体之间的合理关系。
"""

def get_within_community_inference_user_prompt(pairs_text, triples_text):
    return f"""
我有一个知识图谱，其中包含多个实体，这些实体在语义上看似相关，但实际上并非直接关联。

以下是一些可能相关的实体对：
{pairs_text}

以下是一些涉及这些实体的现有关系：
{triples_text}

请推断这些不相关的实体对之间可能存在的关系。
请以以下格式的三元组 JSON 数组形式返回您的答案：

[
{{
"subject": "entity1",
"predicate": "推断的关系",
"object": "entity2"
}},
...
]

仅包含具有明确谓词且高度合理的关系。
重要提示：推断的关系（谓词）不得超过 3 个词。最好是 1-2 个词。切勿超过 3 个。
重要提示：请确保主语和宾语是不同的实体 - 避免自引用。
""" 