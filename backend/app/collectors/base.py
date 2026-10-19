from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol

import httpx


USER_AGENT = "EducatorResearchCollector/2.0 (local research tool; respectful metadata access)"


@dataclass(slots=True)
class Candidate:
    kind: str
    external_id: str
    title: str
    source_name: str
    source_url: str
    description: str = ""
    publication_date: date | None = None
    educator_name: str = ""
    authors: list[str] = field(default_factory=list)
    identifiers: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    copyright_status: str = "unknown"
    access_level: str = "public"
    fulltext_allowed: bool = False
    license_code: str = "unknown"
    license_url: str = ""
    media_url: str = ""
    embed_url: str = ""
    duration_seconds: float | None = None
    embed_allowed: bool = False
    subtitle_access: bool = False
    download_allowed: bool = False
    transcription_allowed: bool = False
    restriction_reason: str = ""


class CollectorError(RuntimeError):
    pass


class SourceAdapter(Protocol):
    key: str

    def search(self, query: str, limit: int = 10, **options: Any) -> list[Candidate]: ...

    def fetch_subtitle(self, external_id: str, language: str) -> str: ...


class HttpAdapter:
    key = "base"

    def __init__(self, timeout: float = 20.0, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )

    def _get_json(self, url: str, *, params: dict[str, Any]) -> dict[str, Any]:
        response = self.client.get(url, params=params)
        if response.status_code == 429:
            raise CollectorError("来源返回 429，任务已按限流规则停止；请稍后恢复")
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise CollectorError("来源返回了非对象 JSON")
        return payload

    def fetch_subtitle(self, external_id: str, language: str) -> str:
        raise CollectorError(f"{self.key} 不提供字幕接口")
