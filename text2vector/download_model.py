from modelscope import snapshot_download

# 下载 bge-m3 向量模型
snapshot_download('BAAI/bge-m3', local_dir='./models/BAAI/bge-m3')

# 下载 bge 重排模型
snapshot_download('BAAI/bge-reranker-v2-m3', local_dir='./models/BAAI/bge-reranker-v2-m3')