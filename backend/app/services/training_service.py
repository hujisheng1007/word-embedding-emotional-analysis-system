import json

from sqlalchemy import and_, select

from app.db.practice_models import PracticeCase, PracticeCaseConcept, PracticeConcept, PracticeRevision
from app.db.research_models import ResearchResource
from app.engines.practice.engine import ANSWER_PROMPT_VERSION, PracticeModel
from app.schemas.practice import FIELD_LABELS, CaseEvaluation, CaseSearch
from app.services.knowledge_service import KnowledgeService, _tokens
from app.services.practice_service import PracticeNotFound, PracticeService, normalize_term

REFLECTIONS = [
    "你的情境与案例有哪些相同与不同？",
    "你会选择尝试哪一步，并用什么观察来判断它是否有帮助？",
]


class TrainingService:
    def __init__(self, practice: PracticeService, model: PracticeModel | None = None) -> None:
        self.practice = practice
        self.model = model or PracticeModel()

    def _visible(self, revision: int | None = None):
        return (
            select(PracticeCase, PracticeRevision)
            .join(PracticeRevision, and_(
                PracticeRevision.case_id == PracticeCase.id,
                PracticeRevision.revision == (revision if revision is not None else PracticeCase.published_revision),
            ))
            .join(ResearchResource, ResearchResource.id == PracticeCase.resource_id)
            .where(
                PracticeCase.published_revision.is_not(None),
                PracticeRevision.revision > PracticeCase.withdrawn_through,
                PracticeRevision.published_at.is_not(None),
                *self.practice.training_source_filters(),
            )
        )

    def _find(self, session, case_id: str, revision: int | None = None):
        row = session.execute(self._visible(revision).where(PracticeCase.id == case_id)).one_or_none()
        if row is None:
            raise PracticeNotFound("案例或版本当前不可用于研习")
        return row

    def case(self, case_id: str, revision: int | None = None) -> dict:
        with self.practice.factory() as session:
            self.practice.check_schema(session)
            case, record = self._find(session, case_id, revision)
            return self.practice.revision_view(session, case, record, public=True)

    def evidence(self, case_id: str, revision: int, evidence_id: str) -> dict:
        case = self.case(case_id, revision)
        for name, field in case["fields"].items():
            for quote in field["evidence"]:
                if quote["id"] == evidence_id:
                    return {"field": name, "source": case["source"], **quote}
        raise PracticeNotFound("该引文在此案例版本中不可用")

    @staticmethod
    def _card(case: PracticeCase, revision: PracticeRevision) -> dict:
        data = json.loads(revision.content_json)
        return {
            "id": case.id, "revision": revision.revision, "title": data["title"],
            "actor_name": data["actor_name"], "applicability": data["applicability"],
            "problem": data["fields"]["problem"]["summary"],
            "strategy": data["fields"]["strategy"]["summary"],
        }

    def browse(self, limit: int, offset: int) -> list[dict]:
        with self.practice.factory() as session:
            self.practice.check_schema(session)
            rows = session.execute(
                self._visible().order_by(PracticeRevision.published_at.desc(), PracticeCase.id)
                .offset(offset).limit(limit)
            )
            return [self._card(case, revision) for case, revision in rows]

    def search(self, payload: CaseSearch) -> list[dict]:
        query = normalize_term(payload.query)
        terms = _tokens(query)
        if not terms:
            return []
        scored = []
        with self.practice.factory() as session:
            self.practice.check_schema(session)
            concept_rows = session.execute(select(PracticeCaseConcept.revision_id, PracticeConcept).join(
                PracticeConcept, PracticeCaseConcept.concept_id == PracticeConcept.id
            ).where(PracticeCaseConcept.revision_id.in_(self._visible().with_only_columns(PracticeRevision.id))))
            concepts_by_revision = {}
            for revision_id, concept in concept_rows:
                concepts_by_revision.setdefault(revision_id, []).append(concept)
            for case, revision in session.execute(self._visible().execution_options(yield_per=100)):
                data = json.loads(revision.content_json)
                body = " ".join(field["summary"] for field in data["fields"].values() if field["state"] == "supported")
                score = KnowledgeService._score(query, terms, data["title"], body)
                matches = []
                for concept in concepts_by_revision.get(revision.id, []):
                    names = [concept.normalized_label, *(normalize_term(alias) for alias in json.loads(concept.aliases_json))]
                    if any(name and name in query for name in names):
                        score += 12 if concept.kind == "problem" else 6
                        matches.append(concept.label)
                if score > 0:
                    scored.append({
                        **self._card(case, revision), "score": round(score, 6),
                        "matched_concepts": sorted(set(matches)),
                    })
        return sorted(scored, key=lambda row: (-row["score"], row["id"]))[:payload.top_k]

    def graph(self, case_id: str, revision_number: int | None = None) -> dict:
        with self.practice.factory() as session:
            self.practice.check_schema(session)
            case, revision = self._find(session, case_id, revision_number)
            document = self.practice.revision_view(session, case, revision, public=True)
            center = f"case:{case.id}"
            nodes = [{
                "id": center, "kind": "case", "label": document["title"],
                "case_id": case.id, "revision": revision.revision,
            }]
            edges = []

            def connect(node_id: str, kind: str, label: str, relation: str, **attrs) -> None:
                nodes.append({"id": node_id, "kind": kind, "label": label, **attrs})
                edges.append({"source": center, "target": node_id, "relation": relation})

            if document["actor_name"]:
                connect(f"actor:{case.id}", "actor", document["actor_name"], "行动主体")
            for concept in document["concepts"]:
                connect(
                    f"concept:{concept['id']}", concept["kind"], concept["label"],
                    {"context": "发生于", "problem": "回应", "strategy": "采用"}[concept["kind"]],
                )
            for name, field in document["fields"].items():
                for evidence in field["evidence"]:
                    connect(
                        f"evidence:{evidence['id']}", "evidence",
                        f"{FIELD_LABELS[name]} · {evidence['locator_value']}", "引证",
                        evidence_id=evidence["id"],
                    )
            problem_ids = [item["id"] for item in document["concepts"] if item["kind"] == "problem"]
            if problem_ids:
                rows = session.execute(
                    self._visible().join(PracticeCaseConcept, PracticeCaseConcept.revision_id == PracticeRevision.id)
                    .where(PracticeCase.id != case.id, PracticeCaseConcept.concept_id.in_(problem_ids))
                    .order_by(PracticeCase.id, PracticeCaseConcept.concept_id).limit(30)
                    .add_columns(PracticeCaseConcept.concept_id)
                )
                seen = set()
                for related, version, concept_id in rows:
                    node_id = f"case:{related.id}"
                    if node_id not in seen:
                        nodes.append({
                            "id": node_id, "kind": "case", "case_id": related.id,
                            "revision": version.revision, "label": json.loads(version.content_json)["title"],
                        })
                        seen.add(node_id)
                    edges.append({"source": node_id, "target": f"concept:{concept_id}", "relation": "回应"})
            return {"center": center, "nodes": nodes, "edges": edges}

    def answer(self, payload: CaseSearch) -> dict:
        matches = self.search(payload)
        evidence = {}
        for match in matches[:5]:
            try:
                document = self.case(match["id"], match["revision"])
            except PracticeNotFound:
                continue
            for name, field in document["fields"].items():
                for quote in field["evidence"][:2]:
                    evidence[quote["id"]] = {
                        **quote, "case_id": match["id"], "revision": match["revision"],
                        "case_title": match["title"], "field": name,
                        "source_title": document["source"]["title"],
                    }
        if not evidence:
            return {
                "mode": "insufficient", "claims": [], "reflection_questions": [],
                "message": "现有已发布案例缺少相关证据。可以补充教学场景、学生表现或已有尝试。",
            }

        try:
            config = self.model.configuration()
            model_input = [
                {key: entry[key] for key in ("id", "quote", "field", "case_title")} for entry in evidence.values()
            ]
            result = self.model.answer(payload.query, model_input, config)
            claims = []
            for claim in result.claims:
                ids = list(dict.fromkeys(claim.evidence_ids))
                if any(evidence_id not in evidence for evidence_id in ids):
                    raise ValueError("模型返回了本次检索范围外的引文")
                claims.append({"text": claim.text, "evidence": [evidence[evidence_id] for evidence_id in ids]})
            response = {
                "mode": "grounded" if claims else "insufficient", "claims": claims,
                "reflection_questions": result.reflection_questions if claims else [],
                "model": {**config, "prompt_version": ANSWER_PROMPT_VERSION},
                "message": "" if claims else "检索结果的原文证据不足以回答这个问题。",
            }
        except ValueError:
            strategies = [entry for entry in evidence.values() if entry["field"] == "strategy"]
            response = {
                "mode": "evidence", "reflection_questions": REFLECTIONS,
                "message": "暂无法生成带引证的回答。下方列出当前检索命中的行动策略原文。",
                "claims": [{"text": entry["quote"], "evidence": [entry]} for entry in strategies[:3]],
            }

        available = {}
        for claim in response["claims"]:
            for quote in claim["evidence"]:
                key = (quote["case_id"], quote["revision"])
                if key not in available:
                    try:
                        self.case(*key)
                        available[key] = True
                    except PracticeNotFound:
                        available[key] = False
        response["claims"] = [
            claim for claim in response["claims"]
            if all(available[(quote["case_id"], quote["revision"])] for quote in claim["evidence"])
        ]
        if not response["claims"] and response["mode"] != "insufficient":
            return {
                "mode": "insufficient", "claims": [], "reflection_questions": [],
                "message": "本次回答所需原文目前不可用，请重新检索。",
            }
        return response

    def evaluate(self, payload: CaseEvaluation) -> dict:
        results = []
        for item in payload.cases:
            hits = self.search(CaseSearch(query=item.query, top_k=payload.top_k))
            ids = [hit["id"] for hit in hits]
            rank = next((index for index, item_id in enumerate(ids, 1) if item_id in item.expected_case_ids), None)
            results.append({"query": item.query, "retrieved_case_ids": ids, "first_relevant_rank": rank})
        return {
            "top_k": payload.top_k, "results": results,
            "hit_rate_at_k": sum(row["first_relevant_rank"] is not None for row in results) / len(results),
            "mean_reciprocal_rank": sum(
                1 / row["first_relevant_rank"] for row in results if row["first_relevant_rank"] is not None
            ) / len(results),
        }
