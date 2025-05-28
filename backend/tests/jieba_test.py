import jieba

text = "后门攻击方法"
seg_list = jieba.cut_for_search(text)

# 转换为数组
tokens = list(seg_list)

print(tokens)
