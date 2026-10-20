from __future__ import annotations

from datetime import date
import os
from typing import Any

from .base import Candidate, HttpAdapter


class OpenAlexWorksAdapter(HttpAdapter):
    key = "openalex"
    endpoint = "https://api.openalex.org/works"

    def search(self, query: str, limit: int = 10, **options: Any) -> list[Candidate]:
        api_key = str(options.get("api_key") or os.getenv("OPENALEX_API_KEY", "")).strip()
        if not api_key:
            raise ValueError(
                "OpenAlex 当前要求 API key。请在 backend/.env 设置 OPENALEX_API_KEY；可在 OpenAlex 官方免费申请。"
            )
        params: dict[str, Any] = {
            "search": query, "per-page": min(max(limit, 1), 25), "api_key": api_key,
        }
        if options.get("email"):
            params["mailto"] = str(options["email"])
        payload = self._get_json(self.endpoint, params=params)
        candidates: list[Candidate] = []
        for work in payload.get("results", []):
            doi = str(work.get("doi") or "").removeprefix("https://doi.org/")
            primary = work.get("primary_location") or {}
            source = primary.get("source") or {}
            oa = work.get("open_access") or {}
            best_oa = work.get("best_oa_location") or {}
            try:
                published = date.fromisoformat(str(work.get("publication_date") or ""))
            except ValueError:
                published = None
            candidates.append(Candidate(
                kind="paper", external_id=str(work.get("id") or doi),
                title=str(work.get("display_name") or "未命名论文"), source_name="OpenAlex",
                source_url=str(work.get("doi") or best_oa.get("landing_page_url") or work.get("id") or ""),
                publication_date=published, educator_name=str(options.get("educator_name") or ""),
                authors=[str(item.get("author", {}).get("display_name")) for item in work.get("authorships", []) if item.get("author", {}).get("display_name")],
                identifiers={"openalex": str(work.get("id") or ""), **({"doi": doi} if doi else {})},
                metadata={"journal": source.get("display_name", ""), "issn_l": source.get("issn_l", ""),
                          "work_type": work.get("type", ""), "cited_by_count": work.get("cited_by_count", 0),
                          "is_oa": bool(oa.get("is_oa")), "oa_status": oa.get("oa_status", ""),
                          "oa_url": best_oa.get("landing_page_url") or best_oa.get("pdf_url") or ""},
                copyright_status="unknown", access_level="public", license_code=str(best_oa.get("license") or "unknown"),
                license_url=str(best_oa.get("landing_page_url") or ""),
                restriction_reason="只登记论文元数据；全文须由开放许可或本地授权导入确认",
            ))
        return candidates
