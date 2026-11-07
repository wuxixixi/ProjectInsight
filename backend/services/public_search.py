"""Public web search adapters used for optional profile enrichment."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

import aiohttp
from aiohttp import ClientResponseError
from email.utils import parsedate_to_datetime

from .news_sources import source_display_name, source_tier


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    content: str
    score: Optional[float] = None
    raw_content: Optional[str] = None
    published_date: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "content": self.content,
            "score": self.score,
            "raw_content": self.raw_content,
            "published_date": self.published_date,
        }


class TavilySearchClient:
    """Minimal Tavily client.

    The API key must be provided through ``TAVILY_API_KEY``. Search results are
    treated as public evidence candidates and should be reviewed before being
    used for individual-level modeling.
    """

    endpoint = "https://api.tavily.com/search"

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 30,
        *,
        include_domains: Optional[Sequence[str]] = None,
        exclude_domains: Optional[Sequence[str]] = None,
        topic: Optional[str] = None,
        time_range: Optional[str] = None,
        include_published_date: bool = False,
    ):
        """构造客户端。

        ``include_domains`` / ``topic`` / ``time_range`` 属于实例级默认约束，
        这样 ``search_with_fallbacks`` 的签名保持不变（现有调用方与测试
        mock 无需改动），同时保证每一次检索都带上来源与时间限定。
        Tavily 官方限制 ``include_domains`` 最多 300 个域名。
        """
        self.api_key = api_key or os.getenv("TAVILY_API_KEY", "").strip()
        self.timeout = timeout
        self.include_domains = list(include_domains) if include_domains else []
        self.exclude_domains = list(exclude_domains) if exclude_domains else []
        self.topic = topic
        self.time_range = time_range
        self.include_published_date = bool(include_published_date)

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        search_depth: str = "basic",
        include_raw_content: bool = False,
    ) -> List[SearchResult]:
        if not self.enabled:
            raise RuntimeError("TAVILY_API_KEY is not configured")
        query = sanitize_query(query)
        if not query:
            return []

        depth = "advanced" if search_depth == "advanced" else "basic"
        payload = {
            "query": query,
            "search_depth": depth,
            "max_results": max(1, min(max_results, 10)),
            "include_answer": False,
            "include_raw_content": bool(include_raw_content),
        }
        # 来源与时间约束：只检索白名单主流媒体、限定为新闻主题、当日发布。
        # 这些字段都是 Tavily Search API 的可选参数，仅在配置时下发。
        if self.include_domains:
            payload["include_domains"] = self.include_domains
        if self.exclude_domains:
            payload["exclude_domains"] = self.exclude_domains
        if self.topic:
            payload["topic"] = self.topic
        if self.time_range:
            payload["time_range"] = self.time_range
        if self.include_published_date:
            payload["include_published_date"] = True
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(self.endpoint, json=payload, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()

        results: List[SearchResult] = []
        for item in data.get("results", []):
            url = str(item.get("url", ""))
            if not url:
                continue
            results.append(
                SearchResult(
                    title=str(item.get("title", "")),
                    url=url,
                    content=str(item.get("content", "")),
                    score=item.get("score"),
                    raw_content=item.get("raw_content") or None,
                    published_date=_normalize_published_date(item.get("published_date")),
                )
            )
        return results

    async def search_with_fallbacks(
        self,
        queries: List[str],
        *,
        max_results: int = 5,
        search_depth: str = "basic",
        include_raw_content: bool = False,
    ) -> List[SearchResult]:
        """Try multiple queries and merge unique results.

        Tavily may reject some CJK-heavy queries as invalid. This method skips
        invalid queries and continues with fallback query variants. When the
        same URL appears across queries, the highest-score hit is kept so the
        body / raw_content reflects the most relevant variant.
        """
        merged: Dict[str, SearchResult] = {}
        for query in queries:
            try:
                results = await self.search(
                    query,
                    max_results=max_results,
                    search_depth=search_depth,
                    include_raw_content=include_raw_content,
                )
            except ClientResponseError as exc:
                if exc.status == 400:
                    continue
                raise
            for result in results:
                existing = merged.get(result.url)
                if existing is None:
                    merged[result.url] = result
                else:
                    new_score = result.score if isinstance(result.score, (int, float)) else 0.0
                    old_score = existing.score if isinstance(existing.score, (int, float)) else 0.0
                    if new_score > old_score:
                        merged[result.url] = result
            if len(merged) >= max_results:
                break
        return list(merged.values())[:max_results]


def sanitize_query(query: str) -> str:
    """Normalize search text before sending it to Tavily."""
    query = (query or "").strip()
    query = re.sub(r"\s+", " ", query)
    query = query.replace("“", '"').replace("”", '"')
    return query[:380]


def _normalize_published_date(value: Any) -> Optional[str]:
    """把 Tavily ``published_date`` 规范成 ``YYYY-MM-DD``。

    Tavily 在 ``topic=news`` 下常返回 RFC 1123 字符串
    （``Fri, 06 Nov 2026 00:00:00 GMT``），也可能返回 ISO 或带时区格式。
    统一成日期字符串，便于前端展示与"是否为今日报道"的判断。
    """
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        dt = parsedate_to_datetime(text)
        if dt is not None:
            return dt.strftime("%Y-%m-%d")
    except (TypeError, ValueError, IndexError):
        pass
    match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", text)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
    return text[:32]


# ============================================================================
# Hot news aggregation helpers
# ============================================================================

# Mapping of common Chinese & international news domains to short display names.
# Hardcoded dict — extend as needed. Fallback is the bare domain.
_DOMAIN_TO_SOURCE: Dict[str, str] = {
    # Chinese state / mainstream media
    "xinhuanet.com": "新华网",
    "news.cn": "新华网",
    "xinhua.com": "新华网",
    "people.com.cn": "人民日报",
    "people.cn": "人民日报",
    "cctv.com": "央视网",
    "cctv.cn": "央视网",
    "china.com.cn": "中国网",
    "china.cn": "中国网",
    "gmw.cn": "光明网",
    "cnr.cn": "央广网",
    "chinanews.com": "中国新闻网",
    "chinadaily.com.cn": "中国日报",
    "chinadaily.cn": "中国日报",
    "thepaper.cn": "澎湃新闻",
    "bjnews.com.cn": "新京报",
    "qq.com": "腾讯新闻",
    "sohu.com": "搜狐新闻",
    "163.com": "网易新闻",
    "sina.com.cn": "新浪新闻",
    "ifeng.com": "凤凰网",
    "guancha.cn": "观察者网",
    "huanqiu.com": "环球网",
    "cnstock.com": "中国证券网",
    "stcn.com": "证券时报",
    "cs.com.cn": "中国证券报",
    "21jingji.com": "21世纪经济报道",
    "yicai.com": "第一财经",
    "caixin.com": "财新网",
    "jiemian.com": "界面新闻",
    # International / English media
    "bbc.com": "BBC",
    "bbc.co.uk": "BBC",
    "reuters.com": "Reuters",
    "apnews.com": "AP News",
    "theguardian.com": "The Guardian",
    "nytimes.com": "New York Times",
    "washingtonpost.com": "Washington Post",
    "cnn.com": "CNN",
    "bloomberg.com": "Bloomberg",
    "wsj.com": "Wall Street Journal",
    "ft.com": "Financial Times",
    "economist.com": "The Economist",
    "cnbc.com": "CNBC",
    "aljazeera.com": "Al Jazeera",
    "france24.com": "France 24",
    "dw.com": "Deutsche Welle",
    "npr.org": "NPR",
    "foxnews.com": "Fox News",
    "abcnews.go.com": "ABC News",
    "nbcnews.com": "NBC News",
    "cbsnews.com": "CBS News",
    "usatoday.com": "USA Today",
    "latimes.com": "Los Angeles Times",
    "scmp.com": "South China Morning Post",
    "nikkei.com": "Nikkei Asia",
    "japantimes.co.jp": "Japan Times",
    "koreaherald.com": "Korea Herald",
    "rt.com": "RT",
    "tass.com": "TASS",
    "xinhua.net": "新华网",
    "globaltimes.cn": "环球时报",
}


def _strip_html(text: str) -> str:
    """Remove HTML tags and collapse whitespace.

    Minimal regex-based sanitizer. Not as robust as BeautifulSoup but adequate
    for Tavily ``raw_content`` which we treat as semi-trusted.
    """
    if not text:
        return ""
    # Remove <script> and <style> blocks entirely (including their content).
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    # Strip remaining tags.
    text = re.sub(r"<[^>]+>", " ", text)
    # Decode a few common HTML entities (we don't pull in html.unescape to keep
    # this module dependency-free).
    text = (
        text.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )
    # Collapse whitespace.
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Tavily raw_content cleanup
# ---------------------------------------------------------------------------
# Tavily returns a Markdown rendering of the *whole* page. On news sites the
# first few thousand characters are usually logos, share buttons, navigation
# menus and footer links -- exactly the noise that used to be injected into the
# simulation as "article body" (e.g. "[![KYODO NEWS](.../logo.svg)](/)").
# The real article sits further down the page, so we must strip chrome rows
# BEFORE applying the 3000-character cap; otherwise the actual text is lost.

_MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_BARE_URL_RE = re.compile(r"(?:https?:)?//[^\s)\]]+")
_ASSET_PATH_RE = re.compile(
    r"(?:https?:)?//[^\s)\]]*\.(?:svg|png|jpe?g|gif|webp|ico|bmp)(?:\?[^\s)\]]*)?",
    re.IGNORECASE,
)
_DECORATION_RE = re.compile(r"^[\s#>*+\-|=_~`\[\]()（）·•:：,，.。/\\|]+$")
_NOISE_KEYWORDS = (
    "copyright", "all rights reserved", "icp备", "icp证", "公网安备",
    "许可证", "网站地图", "广告服务", "供稿服务", "法律声明", "招聘信息",
    "关于我们", "about us", "联系我们", "友情链接", "举报", "大字体", "小字体",
    "打印本页", "关闭窗口", "分享到", "扫一扫", "二维码", "上一篇", "下一篇",
    "previous next", "责任编辑", "相关新闻", "热门推荐", "返回顶部", "版权所有",
    "未经授权", "转载请", "订阅", "rss", "language", "首页 →",
    "up next", "ie 11 is not supported", "sign in", "advertisement",
    "subscribe now", "follow us", "read more", "share this", "newsletter",
)


def _substantive_chars(text: str) -> int:
    """Count letters/CJK characters so Chinese and English share one scale."""
    return sum(1 for ch in (text or "") if ch.isalpha() or "\u3040" <= ch <= "\u30ff")


def _clean_markdown_line(line: str) -> str:
    """Strip Markdown images/links/URLs from one row, keeping link labels."""
    if not line:
        return ""
    # Kill asset URLs first so "[![alt](logo.svg)](link)" becomes removable.
    cleaned = _ASSET_PATH_RE.sub(" ", line)
    for _ in range(3):  # handles wrapped images / nested link syntax
        new = _MD_IMAGE_RE.sub(" ", cleaned)
        new = _MD_LINK_RE.sub(r"\1", new)
        if new == cleaned:
            break
        cleaned = new
    cleaned = _BARE_URL_RE.sub(" ", cleaned)
    # Nested / malformed Markdown: Tavily sometimes emits ")" inside URLs,
    # leaving fragments such as "](https://...)". Scrub those too.
    cleaned = re.sub(r"\]\s*\([^)]*\)", " ", cleaned)
    cleaned = re.sub(r"\[[^\]]{0,80}\]\s*\([^)]*\)", " ", cleaned)
    cleaned = cleaned.replace("](", " ")
    cleaned = re.sub(r"^[\s#>*+\-|]+", " ", cleaned)
    # Leftover empty brackets/parentheses from stripped images.
    cleaned = re.sub(r"[\[\]\(\)（）]{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" \t|*+-#>")
    if _DECORATION_RE.match(cleaned):
        return ""
    return cleaned


def _is_noise_line(original: str, cleaned: str) -> bool:
    """Return True for navigation/footer rows rather than article prose."""
    if not cleaned:
        return True
    substantive = _substantive_chars(cleaned)
    if substantive < 12:
        return True
    lower = cleaned.lower()
    if any(kw in lower for kw in _NOISE_KEYWORDS):
        return True
    # Link-dense rows are menus,友情链接 or "related news" lists -- even when
    # their link labels add up to a long string of place/organisation names.
    if original.count("](") >= 3:
        return True
    # Pipe-separated region/column navigation (安徽|北京|重庆|...) and
    # Markdown table placeholders such as "|  |".
    if cleaned.count("|") >= 2:
        return True
    return False


def _clean_article_text(text: str) -> str:
    """Extract readable article paragraphs from a Tavily Markdown page dump."""
    if not text:
        return ""
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    kept: List[str] = []
    for raw_line in text.splitlines():
        original = re.sub(r"<[^>]+>", " ", raw_line)
        cleaned = _clean_markdown_line(original)
        if _is_noise_line(original, cleaned):
            continue
        kept.append(cleaned)
    return "\n".join(kept).strip()


def _article_quality(text: str) -> int:
    """Score by the longest remaining paragraph: real prose, not menu items."""
    if not text:
        return 0
    return max((_substantive_chars(line) for line in text.splitlines()), default=0)


def _domain_to_source(url: str) -> str:
    """Map a news URL to a short human-readable source name.

    Mainstream whitelist media use the canonical display name from
    ``news_sources``. Falls back to ``host`` (with leading ``www.`` stripped
    and common TLDs trimmed) if no explicit mapping is registered.
    """
    if not url:
        return ""
    # 主流媒体优先取白名单中的规范名称（含子域名，如 finance.people.com.cn）。
    canonical = source_display_name(url)
    if canonical:
        return canonical
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return ""
    host = host.strip()
    if not host:
        return ""
    if host in _DOMAIN_TO_SOURCE:
        return _DOMAIN_TO_SOURCE[host]
    # Try parent domain (e.g. "news.bbc.com" → "bbc.com").
    parts = host.split(".")
    if len(parts) >= 2:
        parent = ".".join(parts[-2:])
        if parent in _DOMAIN_TO_SOURCE:
            return _DOMAIN_TO_SOURCE[parent]
    # Strip leading "www." and a few common multi-part suffixes for readability.
    bare = host[4:] if host.startswith("www.") else host
    for suffix in (".com.cn", ".co.uk", ".com", ".cn", ".net", ".org"):
        if bare.endswith(suffix):
            bare = bare[: -len(suffix)]
            break
    return bare or host


def _normalize_url(url: str) -> str:
    """Normalize URL for cross-query deduplication.

    Strips the scheme, lowercases the host, removes trailing slash, and drops
    common tracking query parameters.
    """
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return url.strip().lower()
    host = (parsed.netloc or "").lower()
    path = parsed.path or ""
    if path.endswith("/"):
        path = path[:-1]
    return f"{host}{path}"


def _pick_body(result: SearchResult, max_chars: int = 3000) -> str:
    """Pick a clean page body, preferring the full article over the snippet.

    Tavily's ``raw_content`` is a Markdown dump of the entire page. We strip
    navigation/logo/footer rows first (see ``_clean_article_text``), then keep
    the result only if at least one substantial prose paragraph survived.
    Otherwise we fall back to Tavily's ``content`` extract, and finally to the
    legacy HTML-stripped text so the field is never empty.
    """
    raw = (result.raw_content or "").strip()
    content = (result.content or "").strip()
    cleaned_raw = _clean_article_text(raw)
    cleaned_content = _clean_article_text(content)

    if _article_quality(cleaned_raw) >= 30:
        cleaned = cleaned_raw
    elif _article_quality(cleaned_content) >= 20:
        cleaned = cleaned_content
    else:
        cleaned = _strip_html(raw or content)

    # Repair common mojibake (Latin-1 re-encoding of UTF-8 bytes) when detected.
    suspicious = ("â", "ä¸", "ï")
    if any(token in cleaned for token in suspicious):
        try:
            repaired = cleaned.encode("latin1", errors="ignore").decode("utf-8", errors="ignore").strip()
            if repaired:
                cleaned = repaired
        except Exception:
            pass
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars].rstrip() + "…"
    return cleaned


def _pick_summary(result: SearchResult, max_chars: int = 200) -> str:
    """Return a one-line summary (Tavily ``content``) trimmed to ``max_chars``."""
    text = (result.content or "").strip()
    cleaned = _clean_article_text(text)
    if _article_quality(cleaned) < 12:
        cleaned = _strip_html(text)
    text = re.sub(r"\s+", " ", cleaned)
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "…"
    return text


def _aggregate_hot_news(
    per_category: List[Tuple[str, List[SearchResult]]],
    *,
    top_n: int = 8,
) -> List[Dict[str, Any]]:
    """Aggregate per-category results and rank by cross-query heat score.

    A story's heat is the sum of Tavily ``score`` across all queries where the
    same normalized URL appears. Stories with the same title but different URLs
    remain distinct items.

    Args:
        per_category: list of ``(category_label, results)`` tuples.
        top_n: number of top items to return.

    Returns:
        Sorted list of dicts ready for serialization, length <= top_n.
    """
    aggregated: Dict[str, Dict[str, Any]] = {}

    for category_label, results in per_category:
        for r in results:
            url = (r.url or "").strip()
            if not url:
                continue
            key = _normalize_url(url)
            if not key:
                continue
            score = float(r.score) if isinstance(r.score, (int, float)) else 0.0
            entry = aggregated.get(key)
            if entry is None:
                entry = {
                    "title": (r.title or "").strip(),
                    "url": url,
                    "categories": set(),
                    "score_sum": 0.0,
                    "appearances": 0,
                    "_primary_result": r,
                }
                aggregated[key] = entry
            entry["score_sum"] += score
            entry["appearances"] += 1
            entry["categories"].add(category_label)
            # Prefer the result that contributed the highest single score so the
            # body / summary are sourced from the most relevant hit.
            existing_score = float(entry["_primary_result"].score) if isinstance(
                entry["_primary_result"].score, (int, float)
            ) else 0.0
            if score > existing_score:
                entry["_primary_result"] = r
            # Keep the longest non-empty title seen for display.
            existing_title = entry["title"]
            new_title = (r.title or "").strip()
            if len(new_title) > len(existing_title):
                entry["title"] = new_title

    ranked: List[Dict[str, Any]] = []
    for key, entry in aggregated.items():
        primary: SearchResult = entry["_primary_result"]
        body = _pick_body(primary)
        summary = _pick_summary(primary)
        # Use the category with the strongest single score as the primary label.
        primary_category = next(iter(entry["categories"]))
        ranked.append(
            {
                "title": entry["title"],
                "url": entry["url"],
                "source": _domain_to_source(entry["url"]),
                "source_tier": source_tier(entry["url"]),
                "category": primary_category,
                "summary": summary,
                "body": body,
                "heat_score": round(entry["score_sum"], 4),
                "published_at": getattr(primary, "published_date", None),
                "_appearances": entry["appearances"],
            }
        )

    ranked.sort(key=lambda x: x["heat_score"], reverse=True)
    for item in ranked:
        item.pop("_appearances", None)
    return ranked[:top_n]