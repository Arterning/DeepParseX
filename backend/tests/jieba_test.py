import jieba

text = "我喜欢使用人工智能来解决问题"
seg_list = jieba.cut_for_search(text)

# 转换为数组
tokens = list(seg_list)

print(tokens)
