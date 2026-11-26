from typing import TYPE_CHECKING

from app.schemas.practice import PublishedCaseCatalog, PublishedCaseLookup, PublishedCaseReference
from app.services.practice_service import PracticeNotFound, normalize_term

if TYPE_CHECKING:
    from app.services.training_service import TrainingService


def _tool(name, description, schema):
    return {
        "type": "function", "function": {
            "name": name, "description": description, "parameters": schema.model_json_schema(),
        },
    }


TRAINING_DATABASE_TOOLS = [
    _tool("browse_published_cases", "分页浏览可用于研习的案例目录，返回教学问题、案例 ID 和版本。", PublishedCaseCatalog),
    _tool("search_published_cases", "按短语检索当前已发布的教学案例，返回问题、策略、案例 ID 和版本。", PublishedCaseLookup),
    _tool("find_related_cases", "沿案例图谱查同一教学问题的其他已发布案例。使用此前返回的案例 ID 和版本。", PublishedCaseReference),
    _tool("get_case_evidence", "取案例字段的逐字引文、证据 ID、来源和原文定位。使用此前返回的案例 ID 和版本。", PublishedCaseReference),
]


class TrainingDatabaseLookup:
    def __init__(self, training: "TrainingService", limit: int) -> None:
        self.training = training
        self.limit = limit
        self.cases: dict[tuple[str, int], dict] = {}
        self.catalog_cards: dict[tuple[str, int], dict] = {}
        self.evidence_cases: dict[tuple[str, int], None] = {}
        self.trace: list[dict] = []

    def invoke(self, name: str, arguments: str) -> dict:
        try:
            if name == "browse_published_cases":
                return self.catalog(PublishedCaseCatalog.model_validate_json(arguments))
            if name == "search_published_cases":
                return self._search(PublishedCaseLookup.model_validate_json(arguments))
            if name not in {"find_related_cases", "get_case_evidence"}:
                return {"error": "未知研习查询工具"}
            reference = PublishedCaseReference.model_validate_json(arguments)
            key = (reference.case_id, reference.revision)
            card = self.cases.get(key) or self.catalog_cards.get(key)
            if card is None:
                return {"error": "请先通过案例目录、检索或图谱取得案例 ID 和版本"}
            result = self._related(reference) if name == "find_related_cases" else self._read_evidence(reference)
            if "error" not in result:
                self.cases.setdefault(key, card)
            return result
        except PracticeNotFound:
            return {"error": "该案例或版本当前不可用于研习"}
        except ValueError:
            return {"error": "查询参数无效，请按工具定义提供参数"}

    def catalog(self, request: PublishedCaseCatalog) -> dict:
        rows = self.training.browse(request.limit + 1, request.offset)
        cards = rows[:request.limit]
        self.catalog_cards.update(
            ((card["id"], card["revision"]), {**card, "match_method": "semantic"}) for card in cards
        )
        self.trace.append({"action": "catalog", "count": len(cards)})
        return {
            "cases": [
                {"id": card["id"], "revision": card["revision"], "title": card["title"], "problem": card["problem"][:450]}
                for card in cards
            ],
            "next_offset": request.offset + request.limit if len(rows) > request.limit else None,
        }

    def _search(self, request: PublishedCaseLookup) -> dict:
        matched: dict[tuple[str, int], dict] = {}
        for query in dict.fromkeys(normalize_term(phrase) for phrase in request.queries):
            cards, _ = self.training._rank_cases(query, request.limit)
            for card in cards:
                key = (card["id"], card["revision"])
                if key not in matched or card["score"] > matched[key]["score"]:
                    matched[key] = {**card, "match_method": "semantic"}
        cards = sorted(matched.values(), key=lambda card: (-card["score"], card["id"]))[:request.limit]
        self.cases.update(((card["id"], card["revision"]), card) for card in cards)
        self.trace.append({"action": "search", "count": len(cards)})
        return {"cases": cards}

    def _related(self, reference: PublishedCaseReference) -> dict:
        graph = self.training.graph(reference.case_id, reference.revision)
        related_nodes = [node for node in graph["nodes"] if node["kind"] == "case" and node["id"] != graph["center"]]
        cards = []
        for node in related_nodes[:5]:
            try:
                document = self.training.case(node["case_id"], node["revision"])
            except PracticeNotFound:
                continue
            card = {
                "id": document["case_id"], "revision": document["revision"], "title": document["title"],
                "actor_name": document["actor_name"], "applicability": document["applicability"],
                "problem": document["fields"]["problem"]["summary"],
                "strategy": document["fields"]["strategy"]["summary"], "match_method": "graph",
            }
            key = (card["id"], card["revision"])
            cards.append(self.cases.setdefault(key, card))
        self.trace.append({"action": "graph", "count": len(cards)})
        return {"cases": cards}

    def _read_evidence(self, reference: PublishedCaseReference) -> dict:
        key = (reference.case_id, reference.revision)
        if key not in self.evidence_cases and len(self.evidence_cases) >= min(self.limit, 5):
            return {"error": "已取得本次研习所需的案例证据"}
        document = self.training.case(*key)
        citations = self.training._evidence_from_case(document)
        self.evidence_cases[key] = None
        self.trace.append({"action": "evidence", "count": len(citations)})
        return {
            "case": self.training._model_case(document),
            "citations": self.training._model_evidence(citations),
        }

    def candidates(self) -> list[dict]:
        keys = dict.fromkeys((*self.evidence_cases, *self.cases))
        return [self.cases[key] for key in list(keys)[:self.limit]]
