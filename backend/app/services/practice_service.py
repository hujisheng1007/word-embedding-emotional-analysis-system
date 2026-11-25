import json
from hashlib import sha256
from unicodedata import normalize
from uuid import uuid4

from sqlalchemy import and_, inspect, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db.practice_models import (
    PracticeCase, PracticeCaseConcept, PracticeConcept, PracticeEvidence,
    PracticeExtractionRun, PracticeRevision, utc_now,
)
from app.db.research_models import ResearchResource, ResourceSegment
from app.db.session import get_session_factory
from app.schemas.practice import (
    FIELD_LABELS, REQUIRED_FIELDS, CaseContent, CreateCase, NewConcept, PublishCase,
    SaveCase, SourceSelection,
)
from app.utils.evidence import resolve_quote

PRACTICE_TABLES = {
    model.__tablename__ for model in (
        PracticeCase, PracticeRevision, PracticeEvidence, PracticeExtractionRun,
        PracticeConcept, PracticeCaseConcept,
    )
}
TRAINING_COPYRIGHT = ("authorized", "public_domain", "fair_use")
TRAINING_ACCESS = ("internal", "public")


class PracticeSchemaNotReady(RuntimeError):
    pass


class PracticeNotFound(ValueError):
    pass


class PracticeConflict(ValueError):
    pass


def json_text(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def fingerprint(value) -> str:
    return sha256(json_text(value).encode("utf-8")).hexdigest()


def normalize_term(text: str) -> str:
    return " ".join(normalize("NFKC", text).casefold().split())


def checked_spans(spans: list[dict], segment_ids: list[str]) -> list[dict]:
    wanted = set(segment_ids)
    ordered = [span for span in spans if span["segment_id"] in wanted]
    if len(ordered) != len(wanted) or len(wanted) != len(segment_ids):
        raise ValueError("片段必须唯一且来自当前资料范围")
    if any(b["ordinal"] != a["ordinal"] + 1 for a, b in zip(ordered, ordered[1:])):
        raise ValueError("请选取同一份材料中的连续片段")
    if not ordered or sum(len(span["text"]) for span in ordered) > 30000:
        raise ValueError("请选取非空且不超过 30,000 字符的原文范围")
    return ordered


def normalize_evidence(content: CaseContent, spans: list[dict]) -> None:
    sources = {span["segment_id"]: span["text"] for span in spans}
    for name, label in FIELD_LABELS.items():
        field = getattr(content.fields, name)
        for evidence in field.evidence:
            if evidence.segment_id not in sources:
                raise ValueError(f"{label}的引文超出了本次原文范围")
            try:
                evidence.start_char, evidence.end_char = resolve_quote(
                    sources[evidence.segment_id], evidence.quote,
                    evidence.start_char, evidence.end_char,
                )
            except ValueError as exc:
                raise ValueError(f"{label}：{exc}") from exc


class PracticeService:
    def __init__(self, factory: sessionmaker | None = None) -> None:
        self.factory = factory or get_session_factory()

    @staticmethod
    def check_schema(session: Session) -> None:
        if PRACTICE_TABLES - set(inspect(session.get_bind()).get_table_names()):
            raise PracticeSchemaNotReady("典范实践模块尚未迁移，请执行 alembic upgrade head")

    @staticmethod
    def require_source(session: Session, resource_id: str) -> ResearchResource:
        resource = session.get(ResearchResource, resource_id)
        if resource is None:
            raise PracticeNotFound("研究资源不存在")
        if not resource.fulltext_allowed or resource.copyright_status == "restricted":
            raise ValueError("该资源未登记可用于研究的全文")
        return resource

    @staticmethod
    def training_source_filters() -> tuple:
        return (
            ResearchResource.fulltext_allowed.is_(True),
            ResearchResource.copyright_status.in_(TRAINING_COPYRIGHT),
            ResearchResource.access_level.in_(TRAINING_ACCESS),
        )

    def source(self, session: Session, payload: SourceSelection) -> dict:
        resource = self.require_source(session, payload.resource_id)
        rows = session.scalars(
            select(ResourceSegment)
            .where(ResourceSegment.resource_id == resource.id, ResourceSegment.id.in_(payload.segment_ids))
            .order_by(ResourceSegment.ordinal)
        ).all()
        spans = [
            {
                "segment_id": row.id, "ordinal": row.ordinal, "text": row.text,
                "locator_type": row.locator_type, "locator_value": row.locator_value,
                "text_sha256": sha256(row.text.encode("utf-8")).hexdigest(),
            }
            for row in rows
        ]
        return {
            "resource_id": resource.id, "title": resource.title,
            "source_institution": resource.source_institution, "source_url": resource.source_url,
            "citation_text": resource.citation_text, "data_version": resource.data_version,
            "spans": checked_spans(spans, payload.segment_ids),
        }

    @staticmethod
    def concept_view(concept: PracticeConcept) -> dict:
        return {
            "id": concept.id, "kind": concept.kind, "label": concept.label,
            "aliases": json.loads(concept.aliases_json),
        }

    def concepts(self) -> list[dict]:
        with self.factory() as session:
            self.check_schema(session)
            rows = session.scalars(select(PracticeConcept).order_by(PracticeConcept.kind, PracticeConcept.label))
            return [self.concept_view(row) for row in rows]

    def create_concept(self, payload: NewConcept) -> dict:
        with self.factory() as session:
            self.check_schema(session)
            normalized = normalize_term(payload.label)
            if len(normalized) > 256:
                raise ValueError("规范词过长")
            aliases = {}
            for alias in payload.aliases:
                key = normalize_term(alias)
                if key and key != normalized:
                    aliases.setdefault(key, alias)
            row = PracticeConcept(
                id=str(uuid4()), kind=payload.kind, label=payload.label,
                normalized_label=normalized, aliases_json=json_text(list(aliases.values())),
            )
            session.add(row)
            try:
                session.commit()
            except IntegrityError as exc:
                raise PracticeConflict("同类型下已存在该规范词，请选择已有词条") from exc
            return self.concept_view(row)

    @staticmethod
    def _case(session: Session, case_id: str) -> PracticeCase:
        case = session.get(PracticeCase, case_id)
        if case is None:
            raise PracticeNotFound("案例不存在")
        return case

    @staticmethod
    def _revision(session: Session, case: PracticeCase, number: int) -> PracticeRevision:
        revision = session.scalar(select(PracticeRevision).where(
            PracticeRevision.case_id == case.id, PracticeRevision.revision == number
        ))
        if revision is None:
            raise PracticeNotFound("案例版本不存在")
        return revision

    @staticmethod
    def _change_version(session: Session, case: PracticeCase, expected_version: int, **values) -> None:
        changed = session.execute(
            update(PracticeCase)
            .where(PracticeCase.id == case.id, PracticeCase.version == expected_version)
            .values(version=expected_version + 1, **values)
            .execution_options(synchronize_session=False)
        )
        if changed.rowcount != 1:
            raise PracticeConflict("案例已更新，请重新载入后再操作")

    def _add_revision(
        self, session: Session, case: PracticeCase, number: int, content: CaseContent
    ) -> None:
        normalize_evidence(content, json.loads(case.source_json)["spans"])
        concept_ids = list(dict.fromkeys(content.concept_ids))
        if concept_ids:
            existing = session.scalars(select(PracticeConcept.id).where(PracticeConcept.id.in_(concept_ids))).all()
            if len(existing) != len(concept_ids):
                raise ValueError("存在未知的案例概念")
        data = content.model_dump(exclude={"concept_ids"})
        revision_id = str(uuid4())
        for field in data["fields"].values():
            field.pop("evidence")
        session.add(PracticeRevision(
            id=revision_id, case_id=case.id, revision=number, content_json=json_text(data),
        ))
        session.flush()
        for name in FIELD_LABELS:
            for evidence in getattr(content.fields, name).evidence:
                session.add(PracticeEvidence(
                    id=str(uuid4()), revision_id=revision_id, field_name=name,
                    segment_id=evidence.segment_id, start_char=evidence.start_char,
                    end_char=evidence.end_char, quote=evidence.quote,
                ))
        session.add_all([
            PracticeCaseConcept(revision_id=revision_id, concept_id=concept_id)
            for concept_id in concept_ids
        ])

    @staticmethod
    def _metadata(revision: PracticeRevision) -> dict:
        return {
            "id": revision.id, "revision": revision.revision, "reviewer": revision.reviewer,
            "review_note": revision.review_note, "created_at": revision.created_at.isoformat(),
            "submitted_at": revision.submitted_at.isoformat() if revision.submitted_at else None,
            "published_at": revision.published_at.isoformat() if revision.published_at else None,
        }

    def revision_view(
        self, session: Session, case: PracticeCase, revision: PracticeRevision, *, public: bool = False
    ) -> dict:
        data = json.loads(revision.content_json)
        source = json.loads(case.source_json)
        spans = {span["segment_id"]: span for span in source["spans"]}
        for field in data["fields"].values():
            field["evidence"] = []
            if public and field["state"] != "supported":
                field["summary"] = ""
        evidence_rows = session.scalars(select(PracticeEvidence).where(
            PracticeEvidence.revision_id == revision.id
        ).order_by(PracticeEvidence.segment_id, PracticeEvidence.start_char, PracticeEvidence.id))
        for evidence in evidence_rows:
            field = data["fields"][evidence.field_name]
            if public and field["state"] != "supported":
                continue
            span = spans[evidence.segment_id]
            field["evidence"].append({
                "id": evidence.id, "segment_id": evidence.segment_id, "quote": evidence.quote,
                "start_char": evidence.start_char, "end_char": evidence.end_char,
                "locator_type": span["locator_type"], "locator_value": span["locator_value"],
                "text_sha256": span["text_sha256"],
            })
        concepts = session.scalars(
            select(PracticeConcept).join(PracticeCaseConcept)
            .where(PracticeCaseConcept.revision_id == revision.id)
            .order_by(PracticeConcept.kind, PracticeConcept.label)
        )
        data["concepts"] = [self.concept_view(row) for row in concepts]
        if public:
            source.pop("spans")
            metadata = {"id": revision.id, "revision": revision.revision}
        else:
            metadata = self._metadata(revision)
        return {"case_id": case.id, "source": source, **metadata, **data}

    def _detail(self, session: Session, case: PracticeCase, number: int | None = None) -> dict:
        revision = self._revision(session, case, number or case.draft_revision)
        history = session.scalars(
            select(PracticeRevision).where(PracticeRevision.case_id == case.id)
            .order_by(PracticeRevision.revision.desc())
        )
        return {
            **self.revision_view(session, case, revision),
            "version": case.version, "draft_revision": case.draft_revision,
            "published_revision": case.published_revision,
            "withdrawn_through": case.withdrawn_through,
            "history": [self._metadata(row) for row in history],
        }

    def create(self, payload: CreateCase) -> dict:
        with self.factory() as session:
            self.check_schema(session)
            source = self.source(session, payload)
            key = fingerprint(["manual", str(payload.request_id or uuid4())])
            return self.create_from_source(session, source, payload.content, key)

    def create_from_source(
        self, session: Session, source: dict, content: CaseContent, key: str
    ) -> dict:
        existing = session.scalar(select(PracticeCase).where(PracticeCase.creation_key == key))
        if existing is not None:
            if existing.source_json != json_text(source):
                raise PracticeConflict("该请求已用于其他原文范围")
            return self._detail(session, existing)
        case = PracticeCase(
            id=str(uuid4()), resource_id=source["resource_id"], creation_key=key,
            source_json=json_text(source),
        )
        session.add(case)
        try:
            session.flush()
            self._add_revision(session, case, 1, content)
            session.commit()
        except IntegrityError:
            session.rollback()
            existing = session.scalar(select(PracticeCase).where(PracticeCase.creation_key == key))
            if existing is None:
                raise
            if existing.source_json != json_text(source):
                raise PracticeConflict("该请求已用于其他原文范围") from None
            case = existing
        return self._detail(session, case)

    def list_cases(self, resource_id: str = "", limit: int = 50, offset: int = 0) -> list[dict]:
        with self.factory() as session:
            self.check_schema(session)
            statement = select(PracticeCase, PracticeRevision).join(PracticeRevision, and_(
                PracticeRevision.case_id == PracticeCase.id,
                PracticeRevision.revision == PracticeCase.draft_revision,
            ))
            if resource_id:
                statement = statement.where(PracticeCase.resource_id == resource_id)
            rows = session.execute(
                statement.order_by(PracticeRevision.created_at.desc(), PracticeCase.id).offset(offset).limit(limit)
            )
            return [
                {
                    "id": case.id, "title": json.loads(revision.content_json)["title"],
                    "resource_id": case.resource_id, "draft_revision": case.draft_revision,
                    "published_revision": case.published_revision, "submitted": bool(revision.submitted_at),
                }
                for case, revision in rows
            ]

    def detail(self, case_id: str, number: int | None = None) -> dict:
        with self.factory() as session:
            self.check_schema(session)
            return self._detail(session, self._case(session, case_id), number)

    def save(self, case_id: str, payload: SaveCase) -> dict:
        with self.factory() as session:
            self.check_schema(session)
            case = self._case(session, case_id)
            self.require_source(session, case.resource_id)
            number = case.draft_revision + 1
            self._change_version(session, case, payload.expected_version, draft_revision=number)
            self._add_revision(session, case, number, payload.content)
            session.commit()
            session.refresh(case)
            return self._detail(session, case)

    def submit(self, case_id: str, expected_version: int) -> dict:
        with self.factory() as session:
            self.check_schema(session)
            case = self._case(session, case_id)
            revision = self._revision(session, case, case.draft_revision)
            if revision.submitted_at:
                raise PracticeConflict("该版本已提交复核")
            self._change_version(session, case, expected_version)
            revision.submitted_at = utc_now()
            session.commit()
            session.refresh(case)
            return self._detail(session, case)

    def publish(self, case_id: str, payload: PublishCase) -> dict:
        with self.factory() as session:
            self.check_schema(session)
            case = self._case(session, case_id)
            revision = self._revision(session, case, case.draft_revision)
            if not revision.submitted_at:
                raise PracticeConflict("请先提交该版本复核")
            if revision.published_at:
                raise PracticeConflict("该版本已有发布记录，请保存新版本后再次发布")
            current_source = self.require_source(session, case.resource_id)
            if (current_source.copyright_status not in TRAINING_COPYRIGHT
                    or current_source.access_level not in TRAINING_ACCESS):
                raise ValueError("资料须登记为开放或内部可用，并注明适用的版权状态，才可发布研习案例")
            document = self.revision_view(session, case, revision)
            missing = [
                FIELD_LABELS[name] for name in REQUIRED_FIELDS
                if document["fields"][name]["state"] != "supported" or not document["fields"][name]["evidence"]
            ]
            if missing:
                raise ValueError("发布前请补全有原文支持的字段：" + "、".join(missing))
            self._change_version(session, case, payload.expected_version, published_revision=revision.revision)
            revision.published_at = utc_now()
            revision.reviewer = payload.reviewer
            revision.review_note = payload.note
            session.commit()
            session.refresh(case)
            return self._detail(session, case)

    def withdraw(self, case_id: str, expected_version: int) -> dict:
        with self.factory() as session:
            self.check_schema(session)
            case = self._case(session, case_id)
            if case.published_revision is None:
                raise PracticeConflict("该案例当前没有已发布版本")
            self._change_version(
                session, case, expected_version, published_revision=None,
                withdrawn_through=case.published_revision,
            )
            session.commit()
            session.refresh(case)
            return self._detail(session, case)
