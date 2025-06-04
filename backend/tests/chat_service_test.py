
import sys

from anyio import run

sys.path.append('../')
from backend.app.admin.service.llm_service import llm_service
from backend.app.admin.service.chat_service import chat_service

async def init() -> None:
    # res = await chat_service.rag_chat(
    #     text="你是何人？",
    # )

    res = await chat_service.generate_summary(
        id=58,
    )
    # res = await llm_service.get_llm_response(
    #     system_context="You are a helpful assistant",
    #     user_input="你是何人？",
    # )
    print(res)

if __name__ == '__main__':
    run(init) 