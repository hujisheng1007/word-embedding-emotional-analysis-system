from __future__ import annotations

import asyncio
from dataclasses import dataclass
import random
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

import aiotieba as tb
from aiotieba.enums import ThreadSortType

from app.schemas.analysis import (
    BatchAnalysisRequest,
    PublicSource,
    PublicSourceFetchResponse,
)
from app.services.analysis_service import AnalysisService


@dataclass(frozen=True)
class PublicSourceDefinition:
    id: str
    name: str
    description: str
    feed_url: str
    source_type: str = "rss"
    forum_name: str = ""


PUBLIC_SOURCES: tuple[PublicSourceDefinition, ...] = (
    PublicSourceDefinition(
        id="xidian-tieba",
        name="西安电子科技大学吧",
        description="点击后按需从西安电子科技大学吧随机抓取一批主题帖标题，适合贴近中文大学生互联网语境的演示。",
        feed_url="https://tieba.baidu.com/f?kw=%E8%A5%BF%E5%AE%89%E7%94%B5%E5%AD%90%E7%A7%91%E6%8A%80%E5%A4%A7%E5%AD%A6",
        source_type="tieba_forum",
        forum_name="西安电子科技大学",
    ),
    PublicSourceDefinition(
        id="v2ex-hot",
        name="V2EX 热门主题",
        description="获取公开社区 V2EX 首页 RSS 标题，用于展示通用互联网公开文本接入。",
        feed_url="https://www.v2ex.com/index.xml",
    ),
    PublicSourceDefinition(
        id="hn-frontpage",
        name="Hacker News Front Page",
        description="获取 Hacker News 首页 RSS 标题，演示英文公开文本的实时分析流程。",
        feed_url="https://news.ycombinator.com/rss",
    ),
)


class PublicDataService:
    def __init__(self, analysis_service: AnalysisService) -> None:
        self.analysis_service = analysis_service

    def list_sources(self) -> list[PublicSource]:
        return [self._to_schema(item) for item in PUBLIC_SOURCES]

    def fetch_and_analyze(self, source_id: str, limit: int = 8) -> PublicSourceFetchResponse:
        source = self._get_source(source_id)
        texts = self._fetch_texts(source, limit=limit)
        if not texts:
            raise ValueError("公开数据源当前没有可分析文本")
        analysis = self.analysis_service.analyze_batch(BatchAnalysisRequest(texts=texts))
        return PublicSourceFetchResponse(
            source=self._to_schema(source),
            fetched_count=len(texts),
            texts=texts,
            analysis=analysis,
        )

    def _fetch_texts(self, source: PublicSourceDefinition, limit: int) -> list[str]:
        if source.source_type == "tieba_forum":
            return self._fetch_tieba_forum_texts(source.forum_name, limit)
        return self._fetch_feed_texts(source.feed_url, limit)

    def _get_source(self, source_id: str) -> PublicSourceDefinition:
        for item in PUBLIC_SOURCES:
            if item.id == source_id:
                return item
        raise ValueError(f"未知公开数据源: {source_id}")

    def _fetch_feed_texts(self, feed_url: str, limit: int) -> list[str]:
        request = Request(
            feed_url,
            headers={
                "User-Agent": "CampusRiskDemo/1.0 (+https://github.com/hujisheng1007/word-embedding-emotional-analysis-system)"
            },
        )
        with urlopen(request, timeout=10) as response:
            content = response.read()

        root = ET.fromstring(content)
        items = self._extract_feed_items(root)
        texts = [item.strip() for item in items if item.strip()]
        return texts[:limit]

    def _fetch_tieba_forum_texts(self, forum_name: str, limit: int) -> list[str]:
        async def _runner() -> list[str]:
            async with tb.Client() as client:
                rng = random.SystemRandom()
                sort_candidates = [ThreadSortType.REPLY, ThreadSortType.CREATE, ThreadSortType.HOT]
                selected_sort = rng.choice(sort_candidates)
                candidate_pages = list(range(1, 7))
                sampled_pages = rng.sample(candidate_pages, k=min(3, len(candidate_pages)))

                texts: list[str] = []
                seen: set[str] = set()

                for page in sampled_pages:
                    threads = await client.get_threads(
                        forum_name,
                        page,
                        rn=min(max(limit * 3, 20), 50),
                        sort=selected_sort,
                    )
                    page_texts = [
                        self._build_tieba_thread_text(thread)
                        for thread in threads
                    ]
                    page_texts = [item for item in page_texts if item]
                    rng.shuffle(page_texts)
                    for text in page_texts:
                        if text in seen:
                            continue
                        seen.add(text)
                        texts.append(text)

                if not texts:
                    threads = await client.get_threads(forum_name, 1, rn=min(max(limit * 3, 20), 50))
                    texts = [
                        self._build_tieba_thread_text(thread)
                        for thread in threads
                    ]
                    texts = [item for item in texts if item]

                rng.shuffle(texts)
                return texts[:limit]

        return asyncio.run(_runner())

    def _build_tieba_thread_text(self, thread) -> str:
        title = self._normalize_text(str(getattr(thread, "title", "")))
        body = self._normalize_text(str(getattr(thread, "text", "")))

        if body.startswith(title):
            body = self._normalize_text(body[len(title):])

        if body:
            body = self._truncate_text(body, 120)
            return f"{title}。{body}" if title else body
        return title

    def _normalize_text(self, text: str) -> str:
        cleaned = text.replace("\r", " ").replace("\n", " ")
        cleaned = " ".join(cleaned.split())
        return cleaned.strip()

    def _truncate_text(self, text: str, limit: int) -> str:
        return text if len(text) <= limit else f"{text[:limit].rstrip()}..."

    def _extract_feed_items(self, root: ET.Element) -> list[str]:
        channel_items = [item.findtext("title", default="") for item in root.findall("./channel/item")]
        if channel_items:
            return channel_items

        atom_items: list[str] = []
        for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
            title = entry.findtext("{http://www.w3.org/2005/Atom}title", default="")
            if title:
                atom_items.append(title)
        return atom_items

    def _to_schema(self, source: PublicSourceDefinition) -> PublicSource:
        return PublicSource(
            id=source.id,
            name=source.name,
            description=source.description,
            feed_url=source.feed_url,
        )
