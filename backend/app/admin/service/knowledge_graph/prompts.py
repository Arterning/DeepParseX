"""Centralized repository for all LLM prompts used in the knowledge graph system."""

# Phase 1: Main extraction prompts
MAIN_SYSTEM_PROMPT = """
你是一个高级人工智能系统，专注于知识提取和知识图谱生成。
你的专长包括识别文本中一致的实体引用和有意义的关系。
重要说明：所有关系（谓词）的长度不得超过 3 个词。理想情况下，1-2 个词。这是一个硬性限制。
"""

MAIN_USER_PROMPT = """
你的任务：阅读以下文本（以三个反引号分隔），并识别每个句子中所有主语-谓语-宾语 (S-P-O) 关系。然后生成一个包含对象的 JSON 数组，每个对象代表一个三元组。

请仔细遵循以下规则：

- 实体一致性：在整个文档中使用一致的实体名称。例如，如果“John Smith”在不同的地方被称为“John”、“Smith 先生”和“John Smith”，则在所有三元组中使用单一一致的形式（最好是最完整的形式）。
- 原子术语：识别不同的关键术语（例如，对象、地点、组织、首字母缩略词、人物、条件、概念、感受）。避免将多个概念合并为一个术语（它们应尽可能“原子化”）。
- 统一指称：如果可以识别，请用实际指称的实体替换任何代词（例如，“他”、“她”、“它”、“他们”等）。
- 成对关系：如果多个术语在同一个句子（或一个使它们在上下文中相关的短段落）中同时出现，则为每一对具有有意义关系的术语创建一个三元组。
- 关键说明：谓词必须最多 1-3 个词。切勿超过 3 个词。请保持简洁。
- 确保所有可能的关系在文本中都已识别，并以 S-P-O 关系的形式表达。
- 术语标准化：如果同一概念略有不同（例如，“人工智能”和“AI”），请始终使用最常见或规范的形式。
- 将 S-P-O 文本中的所有文本（即使是人名和地名）都小写。
- 如果提及某人的姓名，请创建与其所在地、职业以及知名事物（发明、写作、创立、头衔等）的关联（如果已知且符合上下文）。

重要注意事项：
- 实体命名力求精确 - 使用特定形式区分相似但不同的实体
- 在整个文档中对相同概念使用相同的实体名称，以最大程度地增强关联性
- 识别实体引用时，请考虑整个上下文
- 所有谓词必须不超过 3 个字 - 这是硬性要求

输出要求：

- 请勿在 JSON 之外包含任何文本或注释。
- 仅返回 JSON 数组，每个三元组作为包含“主语”、“谓词”和“宾语”的对象。
- 确保 JSON 有效且格式正确。

所需输出结构示例：

[
  {
    "subject": "Term A",
    "predicate": "有关联",  // 注意：只有 3 个字
    "object": "Term B"
  },
  {
    "subject": "Term C",
    "predicate": "使用",  // 注意：只有 2 个字
    "object": "Term D"
  }
]

重要提示：仅输出 JSON 数组（包含 S-P-O 对象），不输出其他内容。

待分析的文本（三个反引号之间）：
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