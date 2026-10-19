from __future__ import annotations

from datetime import date
from typing import Any

from .base import Candidate, HttpAdapter


class WikidataPersonAdapter(HttpAdapter):
    key = "wikidata"
    endpoint = "https://www.wikidata.org/w/api.php"

    def search(self, query: str, limit: int = 10, **options: Any) -> list[Candidate]:
        language = str(options.get("language") or "zh")
        payload = self._get_json(self.endpoint, params={
            "action": "wbsearchentities", "search": query, "language": language,
            "uselang": language, "type": "item", "limit": min(max(limit, 1), 25), "format": "json",
        })
        candidates: list[Candidate] = []
        for item in payload.get("search", []):
            entity_id = str(item.get("id") or "")
            if not entity_id:
                continue
            label = str(item.get("label") or entity_id)
            candidates.append(Candidate(
                kind="person", external_id=entity_id, title=label, source_name="Wikidata",
                source_url=str(item.get("concepturi") or f"https://www.wikidata.org/wiki/{entity_id}"),
                description=str(item.get("description") or ""), educator_name=label,
                identifiers={"wikidata": entity_id},
                metadata={"aliases": item.get("aliases", []), "match": item.get("match", {})},
                copyright_status="public_domain", access_level="public", license_code="CC0-1.0",
                license_url="https://creativecommons.org/publicdomain/zero/1.0/",
            ))
        return candidates

    def entity_facts(self, entity_id: str, language: str = "zh") -> dict[str, Any]:
        payload = self._get_json(self.endpoint, params={
            "action": "wbgetentities", "ids": entity_id, "languages": f"{language}|en",
            "props": "labels|descriptions|aliases|claims|sitelinks", "format": "json",
        })
        entity = payload.get("entities", {}).get(entity_id, {})
        return entity if isinstance(entity, dict) else {}

    @staticmethod
    def time_claim(entity: dict[str, Any], property_id: str) -> date | None:
        try:
            raw = entity["claims"][property_id][0]["mainsnak"]["datavalue"]["value"]["time"]
            year, month, day = [int(part) for part in raw.lstrip("+").split("T", 1)[0].split("-")]
            return date(year, max(month, 1), max(day, 1))
        except (IndexError, KeyError, TypeError, ValueError):
            return None
