#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Development server runner that properly sets up the Python path."""
import sys
import argparse  # 新增：导入参数解析模块
from pathlib import Path

# Add parent directory to Python path so 'backend' module can be imported
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

def main():
    # 1. 创建参数解析器
    parser = argparse.ArgumentParser(
        description="Run the backend development server with configurable host/port"
    )
    # 2. 添加参数：host（默认 localhost）、port（默认 8000）
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",  # 默认值改为 localhost
        help="Server host (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,  # 限定为整数，避免非数字端口报错
        default=8001,
        help="Server port (default: 8001)"
    )
    # 3. 解析命令行参数
    args = parser.parse_args()

    # 4. 启动 uvicorn 服务（使用解析后的参数）
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        workers=5,
        host=args.host,
        port=args.port,
        reload=True,
        reload_dirs=[str(Path(__file__).parent)]
    )

if __name__ == "__main__":
    main()