"""
OCR API 配置 —— 所有可调参数集中管理。
"""

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    # ---- 引擎 ----
    default_lang: str = "ch"            # 默认 OCR 语言
    default_backend: str = "pipeline"   # pipeline | vlm-engine | hybrid-engine
    parse_method: str = "auto"          # auto | txt | ocr

    # ---- 输出 ----
    output_dir: str = "./output"        # 解析结果落盘目录

    # ---- 服务 ----
    host: str = "0.0.0.0"
    port: int = 8000

    # ---- 限制 ----
    max_file_mb: int = 100
    cleanup_after_parse: bool = True    # 解析完是否清理落盘文件

    def __post_init__(self):
        # 允许环境变量覆盖：OCR_HOST, OCR_PORT, ...
        for f in self.__dataclass_fields__:
            env_val = os.environ.get(f"OCR_{f.upper()}")
            if env_val is not None:
                target_type = type(getattr(self, f))
                if target_type is bool:
                    setattr(self, f, env_val.lower() in ("1", "true", "yes"))
                else:
                    setattr(self, f, target_type(env_val))


settings = Settings()
