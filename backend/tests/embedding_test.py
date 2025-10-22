
import sys

from anyio import run

sys.path.append('../')

from backend.app.admin.utils.text_processor import embed_text_chunks

async def init() -> None:
    res = await embed_text_chunks(
        text="请生成以下文本的简洁的摘要，突出核心内容。请你必须使用中文描述，不超过500字：",
    )
    print(res)

if __name__ == '__main__':
    run(init)