"""主流媒体来源白名单与可信度分级。

背景：`GET /api/event/hot-news` 早期直接用宽泛关键词调用 Tavily，返回结果里
混入了采集站、山寨"新闻中心"、WordPress 主题演示站、百度百科词条、门户自媒体
号等"来源不正"的页面，甚至不是当天新闻。本模块把来源治理集中到一处：

1. 分级维护主流媒体域名白名单（中央主要新闻单位 / 全国性权威媒体 / 国际主流媒体）。
2. 白名单域名用于 Tavily ``include_domains``，从检索源头限定站点。
3. 对返回结果做二次校验（防御性兜底，防止 API 越界返回）。
4. 为前端提供规范的来源名称与可信等级。

设计原则：白名单（allow-list）而非黑名单。互联网上不可信站点是无穷集合，
只有"具备新闻采编资质的主流媒体 + 官方发布机构"才允许进入推演事件源。

分级含义：
- Tier 1：中央主要新闻单位、国家级权威媒体、政府官方发布
- Tier 2：全国性主流市场化媒体、权威财经媒体
- Tier 3：国际主流通讯社与权威媒体（补充国际视角）
"""
from __future__ import annotations

from typing import Dict, FrozenSet, Iterable, List, Optional, Tuple, TypeVar
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Tier 1 — 中央主要新闻单位 / 国家级权威媒体 / 官方发布
# ---------------------------------------------------------------------------
TIER_1: Dict[str, str] = {
    "xinhuanet.com": "新华网",
    "news.cn": "新华社",
    "xinhua.net": "新华网",
    "people.com.cn": "人民网",
    "people.cn": "人民网",
    "cctv.com": "央视网",
    "cctv.cn": "央视网",
    "cnr.cn": "央广网",
    "cri.cn": "国际在线",
    "china.com.cn": "中国网",
    "gmw.cn": "光明网",
    "chinanews.com.cn": "中国新闻网",
    "chinanews.com": "中国新闻网",
    "chinadaily.com.cn": "中国日报",
    "ce.cn": "中国经济网",
    "cnfin.com": "新华财经",
    "stdaily.com": "科技日报",
    "cyol.com": "中国青年报",
    "jyb.cn": "中国教育新闻网",
    "workercn.cn": "中工网",
    "legaldaily.com.cn": "法治日报",
    "farmer.com.cn": "农民日报",
    "globaltimes.cn": "环球时报",
    "huanqiu.com": "环球网",
    "gov.cn": "中国政府网",
}

# ---------------------------------------------------------------------------
# Tier 2 — 全国性主流市场化媒体 / 权威财经媒体
# ---------------------------------------------------------------------------
TIER_2: Dict[str, str] = {
    "thepaper.cn": "澎湃新闻",
    "bjnews.com.cn": "新京报",
    "caixin.com": "财新网",
    "yicai.com": "第一财经",
    "jiemian.com": "界面新闻",
    "21jingji.com": "21世纪经济报道",
    "stcn.com": "证券时报",
    "cs.com.cn": "中国证券报",
    "cnstock.com": "上海证券报",
    "eeo.com.cn": "经济观察网",
    "nbd.com.cn": "每日经济新闻",
    "cb.com.cn": "中国经营报",
    "infzm.com": "南方周末",
    "oeeee.com": "南方都市报",
    "inewsweek.cn": "中国新闻周刊",
    "lifeweek.com.cn": "三联生活周刊",
    "jfdaily.com": "上观新闻",
    "shobserver.com": "上观新闻",
    "thecover.cn": "封面新闻",
}

# ---------------------------------------------------------------------------
# Tier 3 — 国际主流通讯社 / 权威媒体（国际分类补充视角）
# 显示名沿用系统既有英文命名，避免前端与历史数据出现不必要差异。
# ---------------------------------------------------------------------------
TIER_3: Dict[str, str] = {
    "reuters.com": "Reuters",
    "apnews.com": "AP News",
    "afp.com": "AFP",
    "bbc.com": "BBC",
    "bbc.co.uk": "BBC",
    "cnn.com": "CNN",
    "nytimes.com": "New York Times",
    "washingtonpost.com": "Washington Post",
    "wsj.com": "Wall Street Journal",
    "ft.com": "Financial Times",
    "bloomberg.com": "Bloomberg",
    "economist.com": "The Economist",
    "theguardian.com": "The Guardian",
    "npr.org": "NPR",
    "cnbc.com": "CNBC",
    "aljazeera.com": "Al Jazeera",
    "dw.com": "Deutsche Welle",
    "france24.com": "France 24",
    "nikkei.com": "Nikkei Asia",
    "asahi.com": "The Asahi Shimbun",
    "kyodonews.net": "Kyodo News",
    "japantimes.co.jp": "Japan Times",
    "koreaherald.com": "Korea Herald",
    "scmp.com": "South China Morning Post",
    "zaobao.com.sg": "联合早报",
    "abcnews.go.com": "ABC News",
    "nbcnews.com": "NBC News",
    "cbsnews.com": "CBS News",
    "usatoday.com": "USA Today",
    "latimes.com": "Los Angeles Times",
    "time.com": "Time",
}

# 合并后的展示名 / 等级 / 白名单。Tavily ``include_domains`` 上限 300，
# 当前约 80 个域名，留足扩展空间。
DISPLAY_NAMES: Dict[str, str] = {**TIER_1, **TIER_2, **TIER_3}
SOURCE_TIERS: Dict[str, int] = {
    **{domain: 1 for domain in TIER_1},
    **{domain: 2 for domain in TIER_2},
    **{domain: 3 for domain in TIER_3},
}
MAINSTREAM_DOMAIN_SET: FrozenSet[str] = frozenset(DISPLAY_NAMES)
MAINSTREAM_DOMAINS: Tuple[str, ...] = tuple(sorted(MAINSTREAM_DOMAIN_SET))

# 按长度降序，保证 ``news.bbc.co.uk`` 优先命中 ``bbc.co.uk`` 而不是更短的域名。
_DOMAINS_BY_LEN: Tuple[str, ...] = tuple(
    sorted(MAINSTREAM_DOMAIN_SET, key=lambda d: (-len(d), d))
)

# 明确不被视为"主流新闻来源"的典型站点，仅用于文档与日志说明。
# 实际拦截依赖上面的白名单，黑名单无法穷举采集站/自媒体。
KNOWN_UNTRUSTED_DOMAINS: FrozenSet[str] = frozenset(
    {
        # 门户 UGC / 自媒体聚合（转载来源不可控）
        "qq.com", "sohu.com", "163.com", "sina.com.cn", "ifeng.com",
        "toutiao.com", "baijiahao.baidu.com", "weibo.com", "zhihu.com",
        "bilibili.com", "douyin.com", "xueqiu.com", "tieba.baidu.com",
        # 百科 / 问答 / 文档，不是新闻
        "baike.baidu.com", "baike.com", "wikipedia.org",
        # 采集站、山寨新闻站、站点演示
        "chinanewscenter.com", "shaoqun.com", "demos.afthemes.com",
        # 非采编类评论站 / 境外宣传机构
        "guancha.cn", "rt.com", "tass.com",
    }
)

_INDEX_PATHS = frozenset(
    {
        "", "/", "/index.html", "/index.htm", "/index.shtml",
        "/index.php", "/home", "/home.html", "/default.html", "/default.htm",
    }
)

T = TypeVar("T")


def _host_from_url(url: str) -> str:
    """从 URL 取出小写主机名（去掉端口与 www.）。"""
    if not url:
        return ""
    try:
        host = (urlparse(url.strip()).hostname or "").lower().strip()
    except Exception:
        return ""
    return host[4:] if host.startswith("www.") else host


def _match_domain(host: str) -> Optional[str]:
    """返回命中的白名单域名（精确或子域后缀，取最长匹配）。"""
    if not host:
        return None
    for domain in _DOMAINS_BY_LEN:
        if host == domain or host.endswith("." + domain):
            return domain
    return None


def resolve_source(url: str) -> Optional[Dict[str, object]]:
    """解析 URL 的主媒体信息；非白名单来源返回 ``None``。

    返回 ``{"domain", "name", "tier"}``，tier 为 1/2/3。
    """
    host = _host_from_url(url)
    domain = _match_domain(host)
    if domain is None:
        return None
    name = DISPLAY_NAMES[domain]
    # *.gov.cn 覆盖了大量中央部委与地方站点，统一显示"中国政府网"会失真。
    if domain == "gov.cn" and host not in ("gov.cn", "www.gov.cn"):
        name = "政府网站"
    return {
        "domain": domain,
        "name": name,
        "tier": SOURCE_TIERS[domain],
    }


def is_mainstream_source(url: str) -> bool:
    """URL 是否属于主流媒体白名单。"""
    return resolve_source(url) is not None


def source_tier(url: str) -> int:
    """返回来源等级 1/2/3；非白名单返回 0。"""
    info = resolve_source(url)
    return int(info["tier"]) if info else 0


def source_display_name(url: str) -> str:
    """返回白名单媒体的规范显示名；非白名单返回空字符串。"""
    info = resolve_source(url)
    return str(info["name"]) if info else ""


def is_index_page(url: str) -> bool:
    """判断是否为首页 / 栏目 / 聚合入口（而非具体新闻文章）。

    实测 Tavily 即使限定 ``topic=news``，仍会返回频道页
    （如 ``thepaper.cn/channel_25950``、``chinanews.com.cn/economic.html``）。
    这类页面不是单篇报道，注入推演没有意义，故在结果层剔除。
    """
    if not url:
        return True
    try:
        path = (urlparse(url.strip()).path or "").rstrip("/").lower()
    except Exception:
        return True
    if path in _INDEX_PATHS:
        return True
    segments = [seg for seg in path.split("/") if seg]
    if not segments:
        return True
    # 明确的栏目 / 标签 / 专题入口。
    markers = (
        "/channel_", "/node_", "/tag/", "/tags/", "/category/",
        "/categories/", "/topic/", "/subject/", "/column/", "/special/",
        "/list/", "/shimen/", "/archive/", "/catalog/", "/latest/",
        "/ranking/", "/rank/", "/news-list/", "/article-list/",
        "/scroll-news/", "/index.",  # 专题聚合页 /all/z/XXX/index.shtml
    )
    if any(marker in path for marker in markers):
        return True
    # 单段且不含数字 ID 的路径基本都是频道页（/finance、/economic.html）。
    # 具体报道 URL 一般含日期或文章 ID 数字。
    if len(segments) == 1 and not any(char.isdigit() for char in segments[0]):
        return True
    return False


def _url_of(obj: object) -> str:
    if isinstance(obj, dict):
        return str(obj.get("url", "") or "")
    return str(getattr(obj, "url", "") or "")


def filter_mainstream(results: Iterable[T], *, drop_index_pages: bool = True) -> List[T]:
    """只保留白名单主流媒体的结果，可选剔除站点首页。

    同时兼容 ``SearchResult`` 对象与 dict。供端点在 Tavily
    ``include_domains`` 之后做防御性二次校验。
    """
    kept: List[T] = []
    for item in results:
        url = _url_of(item)
        if not url or not is_mainstream_source(url):
            continue
        if drop_index_pages and is_index_page(url):
            continue
        kept.append(item)
    return kept
