from typing import List
import re

def highlight_text(original: str, keywords: List[str], start_tag='<mark>', end_tag='</mark>') -> str:
    # 排序让更长的关键词先替换，避免短词抢占位置
    sorted_keywords = sorted(keywords, key=len, reverse=True)
    for kw in sorted_keywords:
        # \b 不适用于中文，这里直接做全文替换（可加上分词定位优化）
        pattern = re.escape(kw)
        original = re.sub(pattern, f'{start_tag}{kw}{end_tag}', original)
    return original


query = "人工智能和人类发展"
# 分词
import jieba
tokens = list(jieba.cut(query))
# highlight content
highlighted = highlight_text("科技是人类进步的阶梯，人工智能是科技的下一阶梯", tokens)
print(highlighted)
