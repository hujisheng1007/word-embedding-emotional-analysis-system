from __future__ import annotations

import html
import re
from typing import Any

from .base import Candidate, CollectorError, HttpAdapter


_TAG_RE = re.compile(r"<[^>]+>")
_OPEN_LICENSES = ("cc by", "cc-by", "cc0", "public domain", "cc by-sa", "cc-by-sa")


def _plain(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("value", "")
    return html.unescape(_TAG_RE.sub("", str(value or ""))).strip()


class WikimediaVideoAdapter(HttpAdapter):
    key = "wikimedia_commons"
    endpoint = "https://commons.wikimedia.org/w/api.php"

    def search(self, query: str, limit: int = 10, **options: Any) -> list[Candidate]:
        payload = self._get_json(self.endpoint, params={
            "action": "query", "generator": "search", "gsrsearch": f"{query} filetype:video",
            "gsrnamespace": 6, "gsrlimit": min(max(limit, 1), 25), "prop": "imageinfo",
            "iiprop": "url|mime|mediatype|extmetadata|size", "format": "json", "formatversion": 2,
        })
        candidates: list[Candidate] = []
        for page in payload.get("query", {}).get("pages", []):
            info = (page.get("imageinfo") or [{}])[0]
            if str(info.get("mediatype") or "").upper() != "VIDEO":
                continue
            metadata = info.get("extmetadata") or {}
            license_code = _plain(metadata.get("LicenseShortName")) or "unknown"
            license_url = _plain(metadata.get("LicenseUrl"))
            open_license = any(marker in license_code.lower() for marker in _OPEN_LICENSES)
            title = str(page.get("title") or "")
            media_url = str(info.get("url") or "")
            candidates.append(Candidate(
                kind="video", external_id=title, title=title.removeprefix("File:"),
                source_name="Wikimedia Commons", source_url=str(info.get("descriptionurl") or ""),
                description=_plain(metadata.get("ImageDescription")),
                educator_name=str(options.get("educator_name") or query),
                metadata={"mime": info.get("mime"), "width": info.get("width"), "height": info.get("height")},
                copyright_status="authorized" if open_license else "unknown", access_level="public",
                license_code=license_code, license_url=license_url,
                media_url=media_url if open_license else "", embed_url=media_url if open_license else "",
                embed_allowed=open_license, subtitle_access=True, download_allowed=open_license,
                transcription_allowed=open_license,
                restriction_reason="" if open_license else "文件页未返回可确认的开放许可；仅登记元数据和原始链接",
            ))
        return candidates

    def fetch_subtitle(self, external_id: str, language: str) -> str:
        response = self.client.get(self.endpoint, params={
            "action": "timedtext", "title": external_id, "lang": language, "trackformat": "vtt",
        }, headers={"Accept": "text/vtt,text/plain;q=0.9"})
        if response.status_code == 404:
            raise CollectorError(f"视频没有 {language} 字幕")
        response.raise_for_status()
        text = response.text.strip()
        if not text.startswith("WEBVTT"):
            raise CollectorError(f"视频没有可用的 {language} WebVTT 字幕")
        return text
