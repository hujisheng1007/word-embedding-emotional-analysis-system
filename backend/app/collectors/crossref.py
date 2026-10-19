from __future__ import annotations

from datetime import date
from typing import Any

from .base import Candidate, HttpAdapter


class CrossrefWorksAdapter(HttpAdapter):
    key = "crossref"
    endpoint = "https://api.crossref.org/works"

    def search(self, query: str, limit: int = 10, **options: Any) -> list[Candidate]:
        params: dict[str, Any] = {
            "query.bibliographic": query, "rows": min(max(limit, 1), 20),
            "select": "DOI,title,author,container-title,published,URL,type,abstract,license",
        }
        if options.get("email"):
            params["mailto"] = str(options["email"])
        payload = self._get_json(self.endpoint, params=params)
        candidates: list[Candidate] = []
        for work in payload.get("message", {}).get("items", []):
            doi = str(work.get("DOI") or "").lower()
            parts = ((work.get("published") or {}).get("date-parts") or [[]])[0]
            try:
                published = date(int(parts[0]), int(parts[1]) if len(parts) > 1 else 1, int(parts[2]) if len(parts) > 2 else 1)
            except (IndexError, TypeError, ValueError):
                published = None
            authors = []
            for author in work.get("author", []):
                name = " ".join(part for part in (author.get("given", ""), author.get("family", "")) if part).strip()
                if name:
                    authors.append(name)
            licenses = work.get("license") or []
            license_url = str(licenses[0].get("URL") or "") if licenses else ""
            candidates.append(Candidate(
                kind="paper", external_id=doi, title=str((work.get("title") or [doi or "未命名论文"])[0]),
                source_name="Crossref", source_url=str(work.get("URL") or f"https://doi.org/{doi}"),
                publication_date=published, educator_name=str(options.get("educator_name") or ""), authors=authors,
                identifiers={"doi": doi} if doi else {},
                metadata={"journal": str((work.get("container-title") or [""])[0]), "work_type": work.get("type", "")},
                copyright_status="unknown", access_level="public",
                license_code="publisher-supplied" if license_url else "unknown", license_url=license_url,
                restriction_reason="Crossref 摘要可能受出版方版权约束；系统只保存检索元数据",
            ))
        return candidates
