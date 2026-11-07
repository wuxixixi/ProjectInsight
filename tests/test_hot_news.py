"""
Tests for GET /api/event/hot-news.

Covers:
- cross-category heat-score aggregation (sum of Tavily scores per URL)
- ``body`` field sourced from ``raw_content`` (with fallback to ``content``)
- ``source`` field derived from URL domain
"""
from __future__ import annotations

import os
from typing import List
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.services.news_sources import (
    filter_mainstream,
    is_index_page,
    is_mainstream_source,
    source_display_name,
    source_tier,
)
from backend.services.public_search import (
    SearchResult,
    TavilySearchClient,
    _aggregate_hot_news,
    _domain_to_source,
    _normalize_published_date,
    _normalize_url,
    _pick_body,
    _pick_summary,
)


# ---------------------------------------------------------------------------
# Pure-function tests (no network)
# ---------------------------------------------------------------------------


class TestDomainToSource:
    """The ``_domain_to_source`` helper should map common news domains."""

    def test_known_chinese_domain(self):
        assert _domain_to_source("https://www.xinhuanet.com/politics/123") == "新华网"

    def test_known_international_domain(self):
        assert _domain_to_source("https://www.bbc.com/news/world-123") == "BBC"

    def test_subdomain_falls_back_to_parent(self):
        # "news.bbc.com" should resolve via the parent mapping "bbc.com".
        assert _domain_to_source("https://news.bbc.com/foo") == "BBC"

    def test_unknown_domain_returns_bare_label(self):
        # Unknown domains fall back to a stripped, human-readable label.
        out = _domain_to_source("https://www.example.org/some/path")
        assert out == "example"

    def test_empty_url_returns_empty_string(self):
        assert _domain_to_source("") == ""


class TestPickBody:
    """``_pick_body`` should prefer ``raw_content`` and fall back to ``content``."""

    def test_prefers_raw_content(self):
        r = SearchResult(
            title="t",
            url="https://x",
            content="snippet text",
            score=0.5,
            raw_content="<p>Full <b>body</b> here.</p>",
        )
        body = _pick_body(r, max_chars=1000)
        assert "Full" in body and "body" in body and "snippet" not in body
        assert "<p>" not in body  # HTML stripped

    def test_falls_back_to_content_when_raw_missing(self):
        r = SearchResult(
            title="t",
            url="https://x",
            content="snippet only",
            score=0.5,
            raw_content=None,
        )
        body = _pick_body(r, max_chars=1000)
        assert "snippet only" in body

    def test_truncates_long_body(self):
        r = SearchResult(
            title="t",
            url="https://x",
            content="x",
            score=0.5,
            raw_content="a" * 5000,
        )
        body = _pick_body(r, max_chars=100)
        assert len(body) <= 102  # 100 + trailing ellipsis allowance
        assert body.endswith("…")


class TestArticleCleanup:
    """Tavily raw_content is a whole-page Markdown dump, not article text.

    Regression coverage for the noise seen in production: Kyodo/中新网/中国网
    pages returned logo SVG links, share buttons and navigation menus as the
    first 3000 characters, so the "原文" panel showed Markdown instead of the
    article.
    """

    NAV_DUMP = """[![KYODO NEWS](https://china-kyodo.ismcdn.jp/common/images/logo.svg)](/)

2026年11月5日 星期四

[![共同社|中文](https://china-kyodo.ismcdn.jp/common/images/logo_text.svg)](/)
* [即时](/scroll-news/news1.html) * [时政](/china/) * [财经](/finance/) * [国际](/world/)
![分享缩略图](http://images.china.cn/images1/ch/2022ChinaIdex/img/shareF2023.png)
# LANGUAGE ## 新闻 [新闻](http://news.china.com.cn/)[直播](http://zhibo.china.com.cn/)
中新社上海11月6日电（记者 肖玉笛）正在上海举行的第九届中国国际进口博览会期间，全球经济再平衡议题受到关注。与会者认为，各国应加强贸易往来、深化产业协同，推动绿色转型和包容发展，以开放合作应对全球经济挑战。
国际贸易中心市场发展司司长表示，中国大市场既为先进制造业提供需求，也为资源型产品和特色农产品创造机会。
Copyright ©1999-2026 chinanews.com. All Rights Reserved
"""

    def test_strips_markdown_images_links_and_navigation(self):
        r = SearchResult(
            title="进博会聚焦全球经济再平衡",
            url="https://www.chinanews.com.cn/gj/2026/11-06/10727109.shtml",
            content="中新社上海11月6日电，进博会期间全球经济再平衡议题受到关注。",
            score=0.8,
            raw_content=self.NAV_DUMP,
        )
        body = _pick_body(r, max_chars=3000)
        assert "中新社上海11月6日电" in body
        assert "国际贸易中心市场发展司司长" in body
        assert "](" not in body
        assert "logo.svg" not in body
        assert "Copyright" not in body
        assert "LANGUAGE" not in body
        assert "scroll-news" not in body

    def test_article_text_survives_when_navigation_is_long(self):
        """Chrome is removed BEFORE truncation, so the real article is kept."""
        head = ("* [栏目](/channel/) * [专题](/topic/) * [新闻](/news/)\n") * 120
        prose = "本报讯 国家统计局今日发布数据，前三季度国内生产总值同比增长5.3%，主要指标保持在合理区间，经济运行总体平稳。" * 3
        r = SearchResult(title="t", url="https://www.xinhuanet.com/politics/20261106/a.html",
                         content="short", score=0.5, raw_content=head + prose)
        body = _pick_body(r, max_chars=3000)
        assert "国家统计局" in body
        assert "栏目" not in body
        assert "](" not in body

    def test_falls_back_to_content_when_page_has_no_prose(self):
        r = SearchResult(title="t", url="https://www.xinhuanet.com/politics/20261106/a.html",
                         content="新华社北京11月6日电，国务院常务会议今日研究部署下一阶段经济工作。",
                         score=0.5,
                         raw_content="* [首页](/) * [登录](/login/)\n![logo](https://x.com/a.svg)\n")
        body = _pick_body(r, max_chars=3000)
        assert "国务院常务会议" in body
        assert "logo" not in body

    def test_strips_partner_links_region_nav_and_malformed_markdown(self):
        dump = """* [中国公共关系协会](http://x.cn/a) [南南合作知识分享](http://x.cn/b) [中国大洋协会](http://x.cn/c) [中国藏学研究中心](http://x.cn/d)
安徽|北京|重庆|福建|甘肃| 贵州|广东|广西|海南|河北| 河南| 湖北|湖南|黑龙江|江苏|江西|
IE 11 is not supported. For an optimal experience visit our site on another browser.
## UP NEXT Protesters rally in several cities.
[Read more](https://www.nbcnews.com/foo_(bar)) [Sign in](https://www.nbcnews.com/login)
The committee said on Thursday that the measure would take effect next month, affecting thousands of commuters across the region.
"""
        r = SearchResult(title="t", url="https://www.nbcnews.com/news/2026/11/a.html",
                         content="The committee said the measure takes effect next month.",
                         score=0.5, raw_content=dump)
        body = _pick_body(r, max_chars=3000)
        assert "The committee said" in body
        assert "中国公共关系协会" not in body
        assert "安徽|北京" not in body
        assert "UP NEXT" not in body
        assert "IE 11" not in body
        assert "](" not in body

    def test_summary_excludes_navigation_rows(self):
        r = SearchResult(title="t", url="https://www.chinanews.com.cn/gj/2026/11-06/1.shtml",
                         content="创意\n\n理论\n\n直播\n\n首页 → 国际新闻\n\n分享到：\n\n"
                                 "中新社上海11月6日电（记者 肖玉笛）正在上海举行的第九届中国国际进口博览会期间，全球经济再平衡议题受到关注。",
                         score=0.5, raw_content=self.NAV_DUMP)
        summary = _pick_summary(r)
        assert "中新社上海11月6日电" in summary
        assert "首页 →" not in summary
        assert "分享到" not in summary


class TestAggregateHotNews:
    """``_aggregate_hot_news`` ranks by summed cross-query score."""

    def test_heat_score_sums_across_categories(self):
        # The same URL appears in two categories with different scores.
        url = "https://www.xinhuanet.com/politics/abc"
        per_category = [
            ("政治", [
                SearchResult(title="A1", url=url, content="c1", score=0.6, raw_content="b1"),
                SearchResult(title="Other", url="https://other.com/x", content="c2", score=0.9, raw_content="b2"),
            ]),
            ("经济", [
                SearchResult(title="A1 again", url=url, content="c1b", score=0.4, raw_content="b1b"),
            ]),
        ]
        ranked = _aggregate_hot_news(per_category, top_n=8)
        assert len(ranked) == 2
        # The shared URL should be ranked first with score = 0.6 + 0.4 = 1.0
        top = ranked[0]
        assert top["url"] == url
        assert top["heat_score"] == pytest.approx(1.0)
        # The other story should have heat_score 0.9.
        other = ranked[1]
        assert other["heat_score"] == pytest.approx(0.9)

    def test_top_n_truncates(self):
        per_category = [
            ("政治", [
                SearchResult(title=f"t{i}", url=f"https://x.com/{i}",
                             content="c", score=1.0 - i * 0.1, raw_content="b")
                for i in range(5)
            ]),
        ]
        ranked = _aggregate_hot_news(per_category, top_n=3)
        assert len(ranked) == 3
        # Highest heat score first.
        assert ranked[0]["heat_score"] == pytest.approx(1.0)
        assert ranked[-1]["heat_score"] < ranked[0]["heat_score"]

    def test_url_normalization_dedups_trailing_slash(self):
        url_a = "https://www.xinhuanet.com/news/abc"
        url_b = "https://www.xinhuanet.com/news/abc/"
        per_category = [
            ("政治", [
                SearchResult(title="a", url=url_a, content="c", score=0.5, raw_content="b"),
            ]),
            ("经济", [
                SearchResult(title="a", url=url_b, content="c", score=0.3, raw_content="b"),
            ]),
        ]
        ranked = _aggregate_hot_news(per_category, top_n=8)
        assert len(ranked) == 1
        assert ranked[0]["heat_score"] == pytest.approx(0.8)

    def test_body_present_in_output(self):
        per_category = [
            ("政治", [
                SearchResult(title="t", url="https://x.com/1",
                             content="snippet", score=0.5,
                             raw_content="<p>Long body text here.</p>"),
            ]),
        ]
        ranked = _aggregate_hot_news(per_category, top_n=8)
        assert ranked[0]["body"]
        assert "Long body text here." in ranked[0]["body"]

    def test_source_is_domain_derived(self):
        per_category = [
            ("政治", [
                SearchResult(title="t", url="https://www.bbc.com/news/x",
                             content="c", score=0.5, raw_content="b"),
            ]),
        ]
        ranked = _aggregate_hot_news(per_category, top_n=8)
        assert ranked[0]["source"] == "BBC"
        assert ranked[0]["source_tier"] == 3


class TestMainstreamSources:
    """来源治理：白名单分级、栏目页识别、结果过滤与日期规范化。"""

    def test_tier_assignment_by_domain(self):
        assert source_tier("http://finance.people.com.cn/n1/2026/1106/c.html") == 1
        assert source_tier("https://www.thepaper.cn/newsDetail_forward_123") == 2
        assert source_tier("https://www.reuters.com/world/china-123/") == 3

    def test_canonical_display_names(self):
        assert source_display_name("https://www.xinhuanet.com/politics/1") == "新华网"
        assert source_display_name("https://www.bbc.com/news/world-1") == "BBC"

    def test_untrusted_sources_rejected(self):
        untrusted = [
            "https://demos.afthemes.com/chromenews/china-news/category/x",
            "https://chinanewscenter.com/archives/tag/x",
            "https://shaoqun.com/s/x.aspx",
            "https://baike.baidu.com/item/x/9053680",
            "https://www.qq.com/news/x",
            "https://evilpeople.com.cn/fake",  # 后缀匹配不能被伪造域名绕过
        ]
        for url in untrusted:
            assert not is_mainstream_source(url), url
            assert source_tier(url) == 0

    def test_index_and_channel_pages_detected(self):
        assert is_index_page("https://www.cnfin.com")
        assert is_index_page("https://www.thepaper.cn/channel_25950")
        assert is_index_page("http://www.chinanews.com.cn/economic.html")
        assert is_index_page("https://www.asahi.com/shimen/20261106")
        assert is_index_page("https://china.kyodonews.net/list/news/economy_science")
        assert is_index_page("https://www.chinanews.com.cn/all/z/ZGGJJKBLH/index.shtml")
        assert not is_index_page(
            "http://politics.people.com.cn/n1/2026/1106/c461001-40829030.html"
        )

    def test_filter_mainstream_keeps_only_whitelisted_articles(self):
        results = [
            SearchResult(title="good", url="https://www.xinhuanet.com/politics/20261106/a1.html",
                         content="c", score=0.9, raw_content="b"),
            SearchResult(title="bad", url="https://chinanewscenter.com/archives/1",
                         content="c", score=0.99, raw_content="b"),
            SearchResult(title="index", url="https://www.thepaper.cn/channel_25950",
                         content="c", score=0.98, raw_content="b"),
        ]
        kept = filter_mainstream(results)
        assert len(kept) == 1
        assert kept[0].url.startswith("https://www.xinhuanet.com/")

    def test_published_date_normalized(self):
        assert _normalize_published_date("Fri, 06 Nov 2026 00:00:00 GMT") == "2026-11-06"
        assert _normalize_published_date("2026-11-06T10:30:00Z") == "2026-11-06"
        assert _normalize_published_date(None) is None


# ---------------------------------------------------------------------------
# Endpoint test (mock Tavily network calls)
# ---------------------------------------------------------------------------


def _make_results(rows: List[dict]) -> List[SearchResult]:
    """Helper: build SearchResult objects from plain dicts."""
    return [
        SearchResult(
            title=row["title"],
            url=row["url"],
            content=row["content"],
            score=row.get("score"),
            raw_content=row.get("raw_content"),
        )
        for row in rows
    ]


@pytest.fixture
def client():
    return TestClient(app)


class TestHotNewsEndpoint:
    """End-to-end tests for ``GET /api/event/hot-news`` with mocked Tavily."""

    def _patch_search_with(self, monkeypatch, per_category_results):
        """Replace ``TavilySearchClient.search_with_fallbacks`` with an AsyncMock.

        ``per_category_results`` is a list aligned with the order of category
        queries in the endpoint (4 categories). Each call returns the next
        bucket so we can model cross-category aggregation.
        """
        iterator = iter(per_category_results)

        async def fake_search_with_fallbacks(
            self, queries, *, max_results=5,
            search_depth="basic", include_raw_content=False,
        ):
            try:
                return next(iterator)
            except StopIteration:
                return []

        # Patch the symbol referenced inside the endpoint module (the endpoint
        # does ``from ..services.public_search import TavilySearchClient`` and
        # uses ``client.search_with_fallbacks``). Patching the bound method on
        # the class covers both call sites.
        monkeypatch.setattr(
            TavilySearchClient,
            "search_with_fallbacks",
            fake_search_with_fallbacks,
        )

    def test_returns_empty_warning_when_api_key_missing(self, client, monkeypatch):
        # The endpoint reads TAVILY_API_KEY via ``load_dotenv`` + ``os.getenv``,
        # so we need to disable ``load_dotenv`` for this test (otherwise it
        # re-populates the env var from ``.env``) and also clear the env var.
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        import backend.routers.event as event_module

        def _noop_load_dotenv(*_args, **_kwargs):
            return False

        monkeypatch.setattr(event_module, "load_dotenv", _noop_load_dotenv)

        resp = client.get("/api/event/hot-news")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0
        assert body["warning"]  # non-empty
        assert "TAVILY_API_KEY" in body["warning"]

    def test_ranks_by_heat_score_and_returns_top_n(self, client, monkeypatch):
        # Ensure the endpoint sees an API key.
        monkeypatch.setenv("TAVILY_API_KEY", "test-key")

        hot_url = "https://www.xinhuanet.com/politics/same-story"
        cool_url = "http://finance.people.com.cn/n1/2026/1106/c1004-40829030.html"

        # Two categories share the hot URL; cool URL appears only once with a
        # very high single score but still loses to the aggregate.
        politics = _make_results([
            {"title": "Hot", "url": hot_url, "content": "p",
             "score": 0.5, "raw_content": "<p>Hot body</p>"},
            {"title": "Cool", "url": cool_url, "content": "c",
             "score": 0.95, "raw_content": "<p>Cool body</p>"},
        ])
        economy = _make_results([
            {"title": "Hot again", "url": hot_url, "content": "p",
             "score": 0.6, "raw_content": "<p>Hot body v2</p>"},
        ])
        culture = _make_results([])
        international = _make_results([])

        self._patch_search_with(
            monkeypatch,
            [politics, economy, culture, international],
        )

        resp = client.get("/api/event/hot-news")
        assert resp.status_code == 200
        data = resp.json()
        assert data["warning"] is None
        assert data["total"] == len(data["items"]) >= 1
        # Top item should be the one whose score summed across categories.
        top = data["items"][0]
        assert top["url"] == hot_url
        assert top["heat_score"] == pytest.approx(1.1)
        # ``body`` should contain the raw_content (HTML stripped).
        assert "Hot body" in top["body"]
        assert "<p>" not in top["body"]
        # ``source`` should be derived from the domain.
        assert top["source"] == "新华网"
        # At most 8 items.
        assert data["total"] <= 8

    def test_body_falls_back_to_content_when_raw_missing(self, client, monkeypatch):
        monkeypatch.setenv("TAVILY_API_KEY", "test-key")

        only_content = _make_results([
            {"title": "Fallback", "url": "https://www.thepaper.cn/newsDetail_forward_30012345",
             "content": "This is a snippet.", "score": 0.7,
             "raw_content": None},
        ])
        self._patch_search_with(
            monkeypatch,
            [only_content, [], [], []],
        )

        resp = client.get("/api/event/hot-news")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert items
        assert items[0]["body"]
        # When raw_content is missing, we should still get the content snippet.
        assert "snippet" in items[0]["body"]

    def test_rejects_non_mainstream_sources(self, client, monkeypatch):
        """采集站 / 百科词条即使分数很高，也不能进入热点新闻列表。"""
        monkeypatch.setenv("TAVILY_API_KEY", "test-key")
        monkeypatch.delenv("HOT_NEWS_STRICT_SOURCES", raising=False)

        mixed = _make_results([
            {"title": "采集站", "url": "https://chinanewscenter.com/archives/tag/x",
             "content": "junk", "score": 0.99, "raw_content": "<p>junk</p>"},
            {"title": "百科词条", "url": "https://baike.baidu.com/item/x/9053680",
             "content": "junk", "score": 0.98, "raw_content": "<p>junk</p>"},
            {"title": "正规报道", "url": "https://www.xinhuanet.com/politics/20261106/a1.html",
             "content": "real", "score": 0.5, "raw_content": "<p>real news</p>"},
        ])
        self._patch_search_with(monkeypatch, [mixed, [], [], []])

        resp = client.get("/api/event/hot-news")
        assert resp.status_code == 200
        data = resp.json()
        assert data["warning"] is None
        assert len(data["items"]) == 1
        assert data["items"][0]["source"] == "新华网"
        assert data["items"][0]["source_tier"] == 1

    def test_warns_when_no_mainstream_results(self, client, monkeypatch):
        """白名单内无结果时给提示，绝不降级回不限定来源的搜索结果。"""
        monkeypatch.setenv("TAVILY_API_KEY", "test-key")
        monkeypatch.delenv("HOT_NEWS_STRICT_SOURCES", raising=False)
        junk = _make_results([
            {"title": "采集站", "url": "https://shaoqun.com/s/x.aspx",
             "content": "junk", "score": 0.9, "raw_content": "junk"},
        ])
        self._patch_search_with(monkeypatch, [junk, [], [], []])

        resp = client.get("/api/event/hot-news")
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert "主流媒体" in (data["warning"] or "")