"""
网络工具执行函数

- web_search: DuckDuckGo Instant Answer API（免费，无需 API Key）
- web_fetch: 抓取网页 → 提取纯文本 → 保存为 sys_doc（type="html"）

注意：web_fetch 结果保存到 sys_doc 表并建立全文索引，
后续可通过 semantic_search / keyword_search 检索到抓取的内容。
"""
import asyncio
import re
import requests
from html.parser import HTMLParser

from backend.common.log import log

# DuckDuckGo Instant Answer API
DUCKDUCKGO_API = "https://api.duckduckgo.com/"

# 请求超时秒数
REQUEST_TIMEOUT = 15


class _TextExtractor(HTMLParser):
    """从 HTML 中提取纯文本，保留段落结构"""

    def __init__(self):
        super().__init__()
        self._text: list[str] = []
        self._skip_tags: set[str] = {"script", "style", "noscript", "head"}
        self._block_tags: set[str] = {
            "p", "div", "h1", "h2", "h3", "h4", "h5", "h6",
            "li", "tr", "br", "hr", "section", "article", "pre",
        }
        self._current_tag: str = ""
        self._skip_depth: int = 0

    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()
        if tag_lower in self._skip_tags:
            self._skip_depth += 1
        if tag_lower in self._block_tags and self._text:
            self._text.append("\n")
        self._current_tag = tag_lower

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in self._skip_tags and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag_lower in self._block_tags and self._text:
            self._text.append("\n")
        self._current_tag = ""

    def handle_data(self, data):
        if self._skip_depth > 0:
            return
        text = data.strip()
        if text:
            self._text.append(text + " ")

    def get_text(self) -> str:
        # 合并空格，合并多余换行
        raw = "".join(self._text)
        raw = re.sub(r" +", " ", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def _extract_title(html: str) -> str:
    """从 HTML 中提取 <title> 文本"""
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if match:
        title = match.group(1).strip()
        # 解码 HTML entities
        title = title.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        title = title.replace("&quot;", '"').replace("&#39;", "'")
        return title
    return ""


def _html_to_text(html: str) -> str:
    """将 HTML 转为纯文本"""
    extractor = _TextExtractor()
    try:
        extractor.feed(html)
    except Exception:
        # 降级：简单去标签
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
    return extractor.get_text()


async def execute_web_search(query: str, max_results: int = 5) -> dict:
    """
    执行网络搜索（DuckDuckGo Instant Answer API）

    返回 JSON 格式的搜索结果列表，包含 title / url / snippet。
    """
    if not query or not query.strip():
        return {"error": "query 不能为空"}

    max_results = min(max(max_results, 1), 10)

    try:
        loop = asyncio.get_running_loop()
        resp = await loop.run_in_executor(
            None,
            lambda: requests.get(
                DUCKDUCKGO_API,
                params={"q": query.strip(), "format": "json", "no_html": 1},
                timeout=REQUEST_TIMEOUT,
            ),
        )

        if resp.status_code not in (200, 202):
            return {"error": f"搜索请求失败: HTTP {resp.status_code}"}

        data = resp.json()
        results: list[dict] = []

        # DuckDuckGo 的 RelatedTopics 包含搜索结果
        for topic in data.get("RelatedTopics", []):
            if topic.get("Text") and topic.get("FirstURL"):
                results.append({
                    "title": topic.get("Text", "").split(" - ")[0].strip() if " - " in topic.get("Text", "") else topic.get("Text", ""),
                    "url": topic.get("FirstURL", ""),
                    "snippet": topic.get("Text", ""),
                })
            if len(results) >= max_results:
                break

        # 如果 RelatedTopics 不够，尝试从 Abstract 补充
        if len(results) < max_results and data.get("AbstractText"):
            abstract_url = data.get("AbstractURL", "")
            if abstract_url:
                results.append({
                    "title": data.get("Heading", "DuckDuckGo Abstract"),
                    "url": abstract_url,
                    "snippet": data.get("AbstractText", ""),
                })

        if not results:
            return {"total": 0, "results": [], "hint": "未找到搜索结果，尝试更具体的关键词"}

        return {
            "total": len(results),
            "query": query,
            "results": results,
        }

    except Exception as e:
        log.error(f"[web_search] 搜索 '{query[:80]}' 失败: {repr(e)}")
        return {"error": repr(e)}


async def execute_web_fetch(url: str, title: str = "") -> dict:
    """
    抓取网页内容，提取纯文本，保存到 sys_doc。

    流程：
    1. HTTP GET 获取 HTML
    2. 提取 <title>（如果未指定 title）
    3. HTML → 纯文本
    4. 保存到 sys_doc（type="html"，建立全文索引）
    """
    if not url or not url.strip():
        return {"error": "url 不能为空"}

    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return {"error": f"不支持的 URL 协议: {url[:50]}"}

    log.info(f"[web_fetch] 抓取: {url[:120]}")

    try:
        loop = asyncio.get_running_loop()
        resp = await loop.run_in_executor(
            None,
            lambda: requests.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                },
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
            ),
        )

        if resp.status_code != 200:
            return {"error": f"抓取失败: HTTP {resp.status_code}"}

        html = resp.text

        # 确定编码
        if resp.encoding and resp.encoding.lower() != "utf-8":
            try:
                html = resp.content.decode(resp.encoding)
            except Exception:
                html = resp.text

        # 提取标题
        if not title:
            title = _extract_title(html)
        if not title:
            title = url.split("/")[-1] or url

        # HTML → 纯文本
        text = _html_to_text(html)

        if not text or len(text.strip()) < 50:
            return {"error": "抓取内容过短或为空，可能是动态页面"}

        # 内容截断（防止超长网页撑爆存储）
        max_chars = 50000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n...[内容过长已截断]"

        # 保存到 sys_doc
        from backend.app.admin.service.doc_service import SysDocService
        from backend.app.admin.schema.doc import CreateSysDocParam

        doc = await SysDocService.create(obj=CreateSysDocParam(
            title=title,
            name=f"{title}.html",
            content=text,
            type="html",
            source=url,
            status=1,
        ))
        # 建立分块和全文检索索引
        await SysDocService.create_doc_tokens(id=doc.id)

        content_preview = text[:300] + ("..." if len(text) > 300 else "")

        log.info(f"[web_fetch] 已保存文档 id={doc.id} title={title!r} len={len(text)}")

        return {
            "success": True,
            "doc_id": doc.id,
            "title": title,
            "url": url,
            "content_length": len(text),
            "content_preview": content_preview,
            "hint": "文档已保存到知识库，可用 semantic_search / keyword_search 检索全文",
        }

    except Exception as e:
        log.error(f"[web_fetch] 抓取 '{url[:120]}' 失败: {repr(e)}")
        return {"error": repr(e)}
