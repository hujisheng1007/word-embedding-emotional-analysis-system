from __future__ import annotations

from typing import Any

from .base import SourceAdapter
from .crossref import CrossrefWorksAdapter
from .openalex import OpenAlexWorksAdapter
from .wikidata import WikidataPersonAdapter
from .wikimedia import WikimediaVideoAdapter


def source_definitions() -> list[dict[str, Any]]:
    return [
        {"name": "Wikidata 教育家人物资料", "adapter_key": "wikidata", "source_type": "person",
         "base_url": "https://www.wikidata.org/", "terms_url": "https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use",
         "robots_url": "https://www.wikidata.org/robots.txt", "license_note": "结构化数据 CC0；候选事实仍需人工审核并保留实体来源",
         "allows_metadata": True, "allows_subtitles": False, "allows_media_download": False,
         "allows_transcription": False, "rate_limit_per_minute": 30},
        {"name": "Wikimedia Commons 教育视频", "adapter_key": "wikimedia_commons", "source_type": "video",
         "base_url": "https://commons.wikimedia.org/", "terms_url": "https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use",
         "robots_url": "https://commons.wikimedia.org/robots.txt", "license_note": "逐文件读取许可；开放许可文件才提供媒体与转写入口，优先导入官方字幕",
         "allows_metadata": True, "allows_subtitles": True, "allows_media_download": True,
         "allows_transcription": True, "rate_limit_per_minute": 20},
        {"name": "OpenAlex 学术论文", "adapter_key": "openalex", "source_type": "paper",
         "base_url": "https://openalex.org/", "terms_url": "https://openalex.org/terms",
         "robots_url": "https://api.openalex.org/robots.txt", "license_note": "检索开放学术元数据；全文许可逐条判断，默认不下载",
         "allows_metadata": True, "allows_subtitles": False, "allows_media_download": False,
         "allows_transcription": False, "rate_limit_per_minute": 30},
        {"name": "Crossref DOI 元数据", "adapter_key": "crossref", "source_type": "paper",
         "base_url": "https://api.crossref.org/", "terms_url": "https://www.crossref.org/documentation/retrieve-metadata/rest-api/",
         "robots_url": "https://api.crossref.org/robots.txt", "license_note": "书目元数据开放；摘要版权可能属于作者或出版方，默认不保存摘要全文",
         "allows_metadata": True, "allows_subtitles": False, "allows_media_download": False,
         "allows_transcription": False, "rate_limit_per_minute": 10},
        {"name": "央视网视频（受限登记）", "adapter_key": "cctv_manual", "source_type": "video",
         "base_url": "https://www.cctv.com/", "terms_url": "https://www.cctv.com/",
         "robots_url": "https://www.cctv.com/robots.txt", "license_note": "当前仅允许人工登记公开页面元数据；不抓取媒体、不绕过播放限制",
         "allows_metadata": True, "allows_subtitles": False, "allows_media_download": False,
         "allows_transcription": False, "rate_limit_per_minute": 6, "enabled": False},
        {"name": "教育部网站（受限登记）", "adapter_key": "moe_manual", "source_type": "webpage",
         "base_url": "http://www.moe.gov.cn/", "terms_url": "http://www.moe.gov.cn/",
         "robots_url": "http://www.moe.gov.cn/robots.txt", "license_note": "当前仅允许人工登记公开页面元数据；未确认许可前不复制正文",
         "allows_metadata": True, "allows_subtitles": False, "allows_media_download": False,
         "allows_transcription": False, "rate_limit_per_minute": 6, "enabled": False},
    ]


def get_adapter(key: str) -> SourceAdapter:
    adapters: dict[str, type] = {
        "wikidata": WikidataPersonAdapter, "wikimedia_commons": WikimediaVideoAdapter,
        "openalex": OpenAlexWorksAdapter, "crossref": CrossrefWorksAdapter,
    }
    adapter_class = adapters.get(key)
    if adapter_class is None:
        raise KeyError(f"来源 {key} 仅支持人工登记或尚未启用自动采集")
    return adapter_class()
