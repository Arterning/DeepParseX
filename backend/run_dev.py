#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Development server runner that properly sets up the Python path."""
import sys
from pathlib import Path

# Add parent directory to Python path so 'backend' module can be imported
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8001,
        reload=True,
        reload_dirs=[str(Path(__file__).parent)]
    )
