"""
Skills Manager

对应 WeKnora skills/manager.go — Manager。
管理技能生命周期：初始化、加载、脚本执行。
"""
import asyncio
import os
import subprocess
import threading
from pathlib import Path
from typing import Optional

from backend.common.log import log
from backend.app.admin.service.agent.skills.loader import SkillLoader, SkillMetadata, Skill

# 脚本执行超时（秒）
DEFAULT_SCRIPT_TIMEOUT = 60

# 脚本执行最大输出字节数
MAX_OUTPUT_BYTES = 50_000


class SkillsManager:
    """
    Skills 管理器。

    使用方式:
        manager = SkillsManager("/path/to/skills")
        manager.initialize()
        metadata = manager.get_all_metadata()  # → 注入 system prompt
    """

    def __init__(self, skills_root: str):
        self._loader = SkillLoader(skills_root)
        self._lock = threading.Lock()
        self._initialized = False

    def initialize(self) -> list[SkillMetadata]:
        """启动时扫描并缓存所有技能元数据"""
        with self._lock:
            result = self._loader.discover()
            self._initialized = True
            log.info(f"[SkillsManager] 初始化完成，发现 {len(result)} 个技能")
            return result

    @property
    def is_enabled(self) -> bool:
        return self._initialized and len(self._loader.get_all_metadata()) > 0

    def get_all_metadata(self) -> list[SkillMetadata]:
        return self._loader.get_all_metadata()

    def load_skill(self, name: str) -> Optional[Skill]:
        """Level 2：加载完整技能指令"""
        return self._loader.load_skill(name)

    def read_skill_file(self, skill_name: str, relative_path: str) -> Optional[str]:
        """Level 3：读取技能目录下的文件"""
        return self._loader.read_skill_file(skill_name, relative_path)

    async def execute_script(
        self,
        skill_name: str,
        script_path: str,
        input_data: str = "",
        args: list[str] | None = None,
        timeout_sec: int = DEFAULT_SCRIPT_TIMEOUT,
    ) -> dict:
        """
        Level 3：在技能目录中执行 Python 脚本。

        安全措施：
        - 工作目录限制为技能目录
        - 超时保护（默认 60s）
        - 输出大小限制（50KB）
        - stdin 传入数据，避免命令行注入

        Returns:
            {"success": bool, "stdout": str, "stderr": str, "exit_code": int}
        """
        meta = self._loader.get_metadata(skill_name)
        if not meta:
            return {"success": False, "error": f"技能不存在: {skill_name}"}

        base = Path(meta.base_path).resolve()
        script = (base / script_path).resolve()

        # 路径穿越防护
        if not str(script).startswith(str(base)):
            return {"success": False, "error": "脚本路径无效"}

        if not script.is_file():
            return {"success": False, "error": f"脚本不存在: {script_path}"}

        args = args or []

        # 在 executor 中运行 subprocess
        loop = asyncio.get_running_loop()

        def _run():
            try:
                proc = subprocess.run(
                    ["python", str(script)] + args,
                    cwd=str(base),
                    input=input_data,
                    capture_output=True,
                    text=True,
                    timeout=timeout_sec,
                    env={
                        **os.environ,
                        "PYTHONIOENCODING": "utf-8",
                    },
                )

                stdout = proc.stdout or ""
                stderr = proc.stderr or ""

                # 截断过长输出
                if len(stdout) > MAX_OUTPUT_BYTES:
                    stdout = stdout[:MAX_OUTPUT_BYTES] + "\n...[输出截断]"
                if len(stderr) > MAX_OUTPUT_BYTES:
                    stderr = stderr[:MAX_OUTPUT_BYTES] + "\n...[输出截断]"

                return {
                    "success": proc.returncode == 0,
                    "stdout": stdout,
                    "stderr": stderr,
                    "exit_code": proc.returncode,
                }
            except subprocess.TimeoutExpired:
                return {"success": False, "error": f"脚本执行超时（{timeout_sec}s）"}
            except Exception as e:
                return {"success": False, "error": f"执行失败: {str(e)}"}

        return await loop.run_in_executor(None, _run)
