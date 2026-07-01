"""
Skills 工具执行函数

- read_skill: 加载技能完整指令（Level 2）
- execute_skill_script: 在技能目录中执行脚本（Level 3）

注意：这些函数依赖 SkillsManager，通过 set_skills_manager() 在启动时注入。
"""
from typing import Optional

from backend.common.log import log

# 模块级 SkillsManager 引用（由外部注入）
_skills_manager: Optional[object] = None


def set_skills_manager(manager):
    """注入 SkillsManager 实例（启动时调用一次）"""
    global _skills_manager
    _skills_manager = manager


def _get_manager():
    if _skills_manager is None:
        raise RuntimeError("SkillsManager 未初始化，请先调用 set_skills_manager()")
    return _skills_manager


async def execute_read_skill(skill_name: str, file_path: str = "") -> dict:
    """
    加载技能完整指令。

    不带 file_path → 返回 SKILL.md 完整指令 + 可用文件列表
    带 file_path   → 返回指定文件内容
    """
    manager = _get_manager()

    # 读取技能目录下的文件
    if file_path:
        content = manager.read_skill_file(skill_name, file_path)
        if content is None:
            return {"error": f"文件不存在或无权访问: {file_path}"}

        return {
            "skill_name": skill_name,
            "file_path": file_path,
            "content": content[:10000],
            "truncated": len(content) > 10000,
        }

    # 加载完整技能指令
    skill = manager.load_skill(skill_name)
    if not skill:
        return {"error": f"技能不存在: {skill_name}"}

    files = skill.list_files()
    scripts = [f for f in files if f.endswith(".py")]
    other_files = [f for f in files if not f.endswith(".py")]

    return {
        "skill_name": skill.name,
        "description": skill.description,
        "instructions": skill.instructions[:8000],
        "truncated": len(skill.instructions) > 8000,
        "available_scripts": scripts,
        "other_files": other_files,
        "hint": (
            f"使用 execute_skill_script(skill_name=\"{skill_name}\", script_path=\"...\") 执行脚本。"
            if scripts else ""
        ),
    }


async def execute_execute_skill_script(
    skill_name: str,
    script_path: str,
    input: str = "",
    args: list[str] | None = None,
) -> dict:
    """
    在技能目录中执行 Python 脚本。

    安全措施：
    - cwd 锁定为技能目录
    - 60s 超时
    - 输出截断 50KB
    """
    manager = _get_manager()

    log.info(f"[execute_skill_script] {skill_name}/{script_path}")

    result = await manager.execute_script(
        skill_name=skill_name,
        script_path=script_path,
        input_data=input or "",
        args=args or [],
    )

    if result.get("success"):
        stdout = result.get("stdout", "")
        return {
            "success": True,
            "skill_name": skill_name,
            "script_path": script_path,
            "output": stdout[:8000],
            "truncated": len(stdout) > 8000,
            "exit_code": result.get("exit_code", 0),
        }
    else:
        return {
            "success": False,
            "skill_name": skill_name,
            "script_path": script_path,
            "error": result.get("error") or result.get("stderr", "未知错误"),
        }
