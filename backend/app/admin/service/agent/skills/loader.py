"""
SKILL.md 文件解析器

对应 WeKnora loader.go — 扫描 skills 目录，解析 YAML frontmatter。
SKILL.md 格式:
---
name: 数据处理器
description: 数据处理与分析技能...
---
# 正文（LLM 指令）
"""
import re
from pathlib import Path
from typing import Optional

import yaml

from backend.common.log import log


class SkillMetadata:
    """Level 1：轻量元数据（始终在 system prompt 中）"""

    def __init__(self, name: str, description: str, base_path: str):
        self.name = name
        self.description = description
        self.base_path = base_path  # 技能目录绝对路径

    def __repr__(self) -> str:
        return f"SkillMetadata(name={self.name!r})"


class Skill:
    """Level 2：完整技能（已加载指令）"""

    def __init__(
        self,
        name: str,
        description: str,
        base_path: str,
        instructions: str,
    ):
        self.name = name
        self.description = description
        self.base_path = base_path
        self.instructions = instructions
        self.loaded = True

    def list_files(self) -> list[str]:
        """列出技能目录下所有非 SKILL.md 文件（相对路径）"""
        base = Path(self.base_path)
        if not base.exists():
            return []
        files = []
        for f in base.rglob("*"):
            if f.is_file() and f.name != "SKILL.md":
                rel = f.relative_to(base)
                files.append(str(rel))
        return sorted(files)


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """
    解析 SKILL.md 的 YAML frontmatter。

    Returns:
        (frontmatter_dict, body_text)
    """
    # 匹配 ---\n...\n--- 之间的内容
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?", content, re.DOTALL)
    if not match:
        raise ValueError("SKILL.md 缺少有效的 YAML frontmatter (---...---)")

    yaml_text = match.group(1)
    body = content[match.end():]

    try:
        frontmatter = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"YAML 解析失败: {e}")

    return frontmatter, body


class SkillLoader:
    """
    Skills 目录加载器。

    对应 WeKnora skills/loader.go — Loader。
    启动时扫描 skills/ 目录，缓存所有 SKILL.md 的元数据。
    """

    def __init__(self, skills_root: str):
        self.skills_root = Path(skills_root).resolve()
        self._metadata_cache: dict[str, SkillMetadata] = {}
        self._instructions_cache: dict[str, str] = {}  # name → instructions

    @property
    def skills_root_path(self) -> Path:
        return self.skills_root

    def discover(self) -> list[SkillMetadata]:
        """
        扫描 skills_root 下所有 SKILL.md，解析 frontmatter 缓存元数据。

        Returns:
            发现的技能元数据列表
        """
        if not self.skills_root.exists():
            log.warning(f"[SkillLoader] skills 目录不存在: {self.skills_root}")
            return []

        self._metadata_cache.clear()
        self._instructions_cache.clear()

        for md_path in sorted(self.skills_root.rglob("*/SKILL.md")):
            try:
                content = md_path.read_text(encoding="utf-8")
                fm, body = _parse_frontmatter(content)

                name = fm.get("name", "").strip()
                description = fm.get("description", "").strip()

                if not name:
                    log.warning(f"[SkillLoader] SKILL.md 缺少 name: {md_path}")
                    continue
                if not description:
                    log.warning(f"[SkillLoader] SKILL.md 缺少 description: {md_path}")
                    continue

                base_dir = str(md_path.parent.resolve())
                self._metadata_cache[name] = SkillMetadata(name, description, base_dir)
                self._instructions_cache[name] = body.strip()
                log.info(f"[SkillLoader] 发现技能: {name} ({md_path})")

            except Exception as e:
                log.warning(f"[SkillLoader] 解析 {md_path} 失败: {repr(e)}")
                continue

        return self.get_all_metadata()

    def get_all_metadata(self) -> list[SkillMetadata]:
        return list(self._metadata_cache.values())

    def get_metadata(self, name: str) -> Optional[SkillMetadata]:
        return self._metadata_cache.get(name)

    def load_skill(self, name: str) -> Optional[Skill]:
        """加载完整技能（含指令）"""
        meta = self._metadata_cache.get(name)
        if not meta:
            return None

        instructions = self._instructions_cache.get(name, "")
        if not instructions:
            # 重新读取
            md_path = Path(meta.base_path) / "SKILL.md"
            if md_path.exists():
                content = md_path.read_text(encoding="utf-8")
                _, instructions = _parse_frontmatter(content)
                self._instructions_cache[name] = instructions.strip()

        return Skill(
            name=meta.name,
            description=meta.description,
            base_path=meta.base_path,
            instructions=instructions.strip(),
        )

    def read_skill_file(self, skill_name: str, relative_path: str) -> Optional[str]:
        """
        读取技能目录下的文件内容。

        对应 WeKnora Loader.LoadSkillFile — 有路径穿越防护。
        """
        meta = self._metadata_cache.get(skill_name)
        if not meta:
            return None

        base = Path(meta.base_path).resolve()
        target = (base / relative_path).resolve()

        # 路径穿越防护
        if not str(target).startswith(str(base)):
            log.warning(f"[SkillLoader] 路径穿越攻击: {relative_path}")
            return None

        if not target.is_file():
            return None

        try:
            return target.read_text(encoding="utf-8")
        except Exception as e:
            log.error(f"[SkillLoader] 读取 {target} 失败: {repr(e)}")
            return None
