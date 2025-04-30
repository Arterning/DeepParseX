
import sys

from anyio import run

sys.path.append('../')

from backend.utils.doc_utils import request_text_to_vector

async def init() -> None:
    res = request_text_to_vector(
        text="请生成以下文本的简洁的摘要，突出核心内容。请你必须使用中文描述，不超过500字：",
    )
    print(res)

if __name__ == '__main__':
    run(init) 