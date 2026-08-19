"""
lda-ocr 启动入口。

Usage:
    python main.py                        # 默认 0.0.0.0:8000
    OCR_PORT=9000 python main.py          # 环境变量覆盖配置
"""

import uvicorn

from src.config import settings


def main():
    uvicorn.run(
        "src.app:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )


if __name__ == "__main__":
    main()
