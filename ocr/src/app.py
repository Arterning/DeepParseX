"""
FastAPI 应用工厂。
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.routes.parse import router as parse_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="lda-ocr",
        description="基于 MinerU 的文档 OCR API",
        version="0.1.0",
    )

    # 路由注册
    app.include_router(parse_router)

    # 全局异常兜底
    @app.exception_handler(Exception)
    async def catch_all(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"detail": f"内部错误: {exc}"},
        )

    return app


app = create_app()
