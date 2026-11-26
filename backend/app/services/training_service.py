import json
import re

from sqlalchemy import and_, select

from app.db.practice_models import PracticeCase, PracticeCaseConcept, PracticeConcept, PracticeEvidence, PracticeRevision
from app.db.research_models import ResearchResource
from app.engines.practice.engine import ANSWER_PROMPT_VERSION, PracticeModel
from app.schemas.practice import (
    FIELD_LABELS, CaseEvaluation, CaseQueryExpansion, CaseSearch, PublishedCaseCatalog, TrainingQuestion,
)
from app.services.knowledge_service import KnowledgeService, _tokens
from app.services.practice_service import PracticeNotFound, PracticeService, normalize_term
from app.services.training_database_lookup import TRAINING_DATABASE_TOOLS, TrainingDatabaseLookup


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

    def _visible_concepts(self):
        return select(PracticeCaseConcept.revision_id, PracticeConcept).join(
            PracticeConcept, PracticeCaseConcept.concept_id == PracticeConcept.id
        ).where(PracticeCaseConcept.revision_id.in_(self._visible().with_only_columns(PracticeRevision.id)))

    def _published_problem_concepts(self, session) -> list[dict]:
        return [
            self.practice.concept_view(concept) for concept in session.scalars(
                select(PracticeConcept)
                .where(
                    PracticeConcept.kind == "problem",
                    PracticeConcept.id.in_(self._visible_concepts().with_only_columns(PracticeConcept.id)),
                )
                .order_by(PracticeConcept.id).limit(60)
            )
        ]

    def _rank_cases(
        self, query: str, top_k: int, expansion: CaseQueryExpansion | None = None,
    ) -> tuple[list[dict], bool]:
        terms = _tokens(query)
        if not terms:
            return [], False
        selected = set(expansion.concept_ids) if expansion else set()
        phrases = {
            term for phrase in (expansion.search_phrases if expansion else [])
            if (term := normalize_term(phrase)) != query and _tokens(term)
        }
        scored = []
        direct_problem_match = False
        with self.practice.factory() as session:
            self.practice.check_schema(session)
            concepts_by_revision = {}
            for revision_id, concept in session.execute(self._visible_concepts()):
                concepts_by_revision.setdefault(revision_id, []).append(concept)
            quotes_by_revision = {}
            visible_revisions = self._visible().with_only_columns(PracticeRevision.id)
            quotes = select(PracticeEvidence.revision_id, PracticeEvidence.field_name, PracticeEvidence.quote).where(
                PracticeEvidence.revision_id.in_(visible_revisions)
            )
            for revision_id, field, quote in session.execute(quotes.execution_options(yield_per=200)):
                quotes_by_revision.setdefault(revision_id, []).append((field, quote))
            for case, revision in session.execute(self._visible().execution_options(yield_per=100)):
                data = json.loads(revision.content_json)
                supported_fields = {
                    name: field["summary"] for name, field in data["fields"].items() if field["state"] == "supported"
                }
                quote_text = " ".join(
                    quote for field, quote in quotes_by_revision.get(revision.id, []) if field in supported_fields
                )
                body = " ".join([*supported_fields.values(), quote_text])
                score = KnowledgeService._score(query, terms, data["title"], body)
                case_text = normalize_term(data["title"] + " " + body) if phrases else ""
                semantic_match = any(phrase in case_text for phrase in phrases)
                if semantic_match:
                    score += 8
                matches = []
                for concept in concepts_by_revision.get(revision.id, []):
                    names = [concept.normalized_label, *(normalize_term(alias) for alias in json.loads(concept.aliases_json))]
                    direct = any(name and name in query for name in names)
                    expanded = concept.id in selected or any(
                        name and name in phrase for phrase in phrases for name in names
                    )
                    if direct and concept.kind == "problem":
                        direct_problem_match = True
                    if direct or expanded:
                        score += 12 if concept.kind == "problem" else 6
                        matches.append(concept.label)
                    if expanded and not direct:
                        semantic_match = True
                        score += 12
                if score > 0:
                    scored.append({
                        **self._card(case, revision), "score": round(score, 6),
                        "matched_concepts": sorted(set(matches)),
                        "match_method": "semantic" if semantic_match else "lexical",
                    })
        ranked = sorted(scored, key=lambda row: (-row["score"], row["id"]))
        return ranked[:top_k], direct_problem_match

    def search(self, payload: CaseSearch) -> list[dict]:
        query = normalize_term(payload.query)
        lexical, direct_problem_match = self._rank_cases(query, payload.top_k)
        if not _tokens(query) or direct_problem_match:
            return lexical
        try:
            config = self.model.configuration()
            with self.practice.factory() as session:
                if not lexical and session.scalar(self._visible().with_only_columns(PracticeCase.id).limit(1)) is None:
                    return []
                concepts = self._published_problem_concepts(session)
            expansion = self.model.interpret_query(payload.query, concepts, config)
        except ValueError:
            return lexical

        allowed_ids = {concept["id"] for concept in concepts}
        expansion.concept_ids = [concept_id for concept_id in expansion.concept_ids if concept_id in allowed_ids]
        if not expansion.concept_ids and not expansion.search_phrases:
            return lexical
        ranked, _ = self._rank_cases(query, payload.top_k, expansion)
        return ranked

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

    @staticmethod
    def _evidence_from_case(document: dict) -> dict[str, dict]:
        return {
            quote["id"]: {
                **quote, "case_id": document["case_id"], "revision": document["revision"],
                "case_title": document["title"], "field": name,
                "source_title": document["source"]["title"],
            }
            for name, field in document["fields"].items()
            for quote in field["evidence"][:2]
        }

    @staticmethod
    def _model_evidence(evidence: dict[str, dict]) -> list[dict]:
        keys = (
            "id", "kind", "quote", "field", "case_id", "revision", "case_title",
            "source_title", "locator_type", "locator_value", "source_file",
        )
        return [{key: entry[key] for key in keys if key in entry} for entry in evidence.values()]

    @staticmethod
    def _model_case(document: dict) -> dict:
        return {
            "case_id": document["case_id"], "revision": document["revision"], "title": document["title"],
            "source_title": document["source"]["title"],
            "concepts": [concept["label"] for concept in document["concepts"]],
            "applicability": document["applicability"][:450],
            "fields": {
                name: {"state": field["state"], "summary": field["summary"][:600]}
                for name, field in document["fields"].items()
            },
        }

    def _currently_visible(self, matches: list[dict]) -> set[tuple[str, int]]:
        if not matches:
            return set()
        with self.practice.factory() as session:
            return set(session.execute(
                self._visible().with_only_columns(PracticeCase.id, PracticeRevision.revision)
                .where(PracticeCase.id.in_([match["id"] for match in matches]))
            ).tuples())

    @staticmethod
    def _evidence_fallback(evidence: dict[str, dict], language: str, *, evidence_changed: bool = False) -> dict:
        quotes = [entry for entry in evidence.values() if entry["field"] in {"strategy", "interview"}][:3]
        if evidence_changed:
            answer = ("The available evidence changed while preparing this reply. Run the question again."
                      if language == "en" else "回答生成期间，可用案例证据发生了变化。请重新提问。")
        elif quotes:
            answer = ("These excerpts offer related teaching experiences. How they apply depends on your classroom situation."
                      if language == "en" else "这些引文记录了可参考的教学经验。是否适用于你的班级取决于具体情境。")
        else:
            answer = ("The available materials provide too little evidence to answer this question."
                      if language == "en" else "现有研习资料暂缺足以回答这个教学问题的证据。")
        return {
            "mode": "evidence" if quotes else "insufficient",
            "answer": answer, "evidence_fit": "indirect" if quotes else "none", "message": "",
            "next_step": "", "clarifying_question": "", "reflection_questions": [],
            "claims": [{"text": entry["quote"], "evidence": [entry]} for entry in quotes],
        }

    def answer(self, payload: TrainingQuestion) -> dict:
        language = "en" if re.search(r"[A-Za-z]{2,}", payload.query) and not re.search(r"[\u3400-\u9fff]", payload.query) else "zh"
        history = {"history": [turn.model_dump() for turn in payload.history]} if payload.history else {}
        try:
            config = self.model.configuration()
        except ValueError:
            config = None

        lookup = TrainingDatabaseLookup(self, payload.top_k)
        has_interviews = lookup.corpus.has_records()
        if config and config.get("provider") == "deepseek":
            catalog = lookup.catalog(PublishedCaseCatalog())
            if catalog["cases"] or has_interviews:
                with self.practice.factory() as session:
                    concepts = self._published_problem_concepts(session)
                try:
                    self.model.lookup_training_database(
                        payload.query, concepts, {**catalog, "interview_rows": lookup.corpus.scanned},
                        TRAINING_DATABASE_TOOLS, lookup.invoke, config, **history,
                    )
                except ValueError:
                    pass

        expansion = None
        if config and not lookup.queries and (has_interviews or history):
            try:
                expansion = self.model.interpret_query(payload.query, [], config, **history)
                expansion.concept_ids = []
            except ValueError:
                pass

        matches = lookup.candidates()
        if matches:
            lexical, _ = self._rank_cases(normalize_term(payload.query), payload.top_k)
            matched_ids = {card["id"] for card in matches}
            matches = (matches + [card for card in lexical if card["id"] not in matched_ids])[:payload.top_k]
        elif expansion and expansion.search_phrases:
            matches, _ = self._rank_cases(normalize_term(payload.query), payload.top_k, expansion)
        else:
            matches = self.search(payload)
        if not matches and history and not (expansion and expansion.search_phrases) and not lookup.queries:
            matches, _ = self._rank_cases(normalize_term(payload.history[-1].question), payload.top_k)
        available = self._currently_visible(matches)
        matches = [match for match in matches if (match["id"], match["revision"]) in available]
        case_context = []
        evidence = {}
        for match in matches[:5]:
            try:
                document = self.case(match["id"], match["revision"])
            except PracticeNotFound:
                continue
            case_context.append(self._model_case(document))
            evidence.update(self._evidence_from_case(document))
        if case_context:
            lookup.trace.append({"action": "context", "count": len(case_context)})
        if has_interviews:
            queries = [payload.query, *sorted(lookup.queries)]
            if expansion and expansion.search_phrases:
                queries.extend(expansion.search_phrases)
            elif history and not lookup.queries:
                queries.append(payload.history[-1].question)
            interviews = lookup.corpus.search(queries, min(payload.top_k, 5))
            evidence.update(interviews)
            lookup.trace.extend([
                {"action": "interview_scan", "count": lookup.corpus.scanned},
                {"action": "interview_context", "count": len(interviews)},
            ])
        try:
            if config is None:
                raise ValueError("强模型未配置")
            result = self.model.answer(
                payload.query, self._model_evidence(evidence), config, cases=case_context, language=language, **history,
            )
            claims = []
            for claim in result.claims:
                ids = list(dict.fromkeys(claim.evidence_ids))
                if any(evidence_id not in evidence for evidence_id in ids):
                    raise ValueError("模型返回了本次检索范围外的引文")
                claims.append({"text": claim.text, "evidence": [evidence[evidence_id] for evidence_id in ids]})
            response = {
                "mode": "grounded" if claims else "insufficient", "claims": claims,
                "answer": result.answer, "evidence_fit": result.evidence_fit,
                "next_step": result.next_step, "clarifying_question": result.clarifying_question,
                "reflection_questions": result.reflection_questions,
                "model": {**config, "prompt_version": ANSWER_PROMPT_VERSION},
                "message": "",
            }
        except ValueError:
            response = self._evidence_fallback(evidence, language)

        available = self._currently_visible(matches)
        visible_matches = [match for match in matches if (match["id"], match["revision"]) in available]
        if any((case["case_id"], case["revision"]) not in available for case in case_context):
            response = self._evidence_fallback({}, language, evidence_changed=True)
        return {**response, "language": language, "matches": visible_matches, "lookup_trace": lookup.trace}

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
