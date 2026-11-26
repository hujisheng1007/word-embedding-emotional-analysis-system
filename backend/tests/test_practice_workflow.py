import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.api.routes import practice as routes
from app.api.routes import research_resources as resource_routes
from app.db.base import Base
from app.db.models import CorpusDataset, CorpusRecord
from app.db.research_models import ResearchResource
from app.engines.practice import engine as practice_engine
from app.main import app
from app.schemas.practice import AnswerClaim, CaseQueryExpansion, ExtractionOutput, ModelAnswer
from app.services.practice_extraction_service import PracticeExtractionService
from app.services.practice_service import PracticeService
from app.services.research_resource_service import ResearchResourceService
from app.services.training_service import TrainingService
from app.utils.evidence import resolve_quote

CONTEXT = "𠮷老师负责组织小组讨论。"
PROBLEM = "小组讨论时只有两名学生发言。"
STRATEGY = "老师请每组轮流安排一名记录员汇报。"


class ModelDouble:
    def __init__(self):
        self.extract_calls = 0
        self.invalid_extraction = False
        self.incorrect_model_offsets = False
        self.invalid_answer = False
        self.query_calls = []
        self.expansion = CaseQueryExpansion()
        self.interpretation_fails = False
        self.suggested_concepts = []
        self.extraction_catalog = []

    def configuration(self):
        return {"profile_id": "test", "model": "test-model"}

    def interpret_query(self, query, concepts, config):
        self.query_calls.append((query, concepts))
        if self.interpretation_fails:
            raise ValueError("模型请求失败")
        return self.expansion.model_copy()

    def extract(self, spans, config, *, concepts=None):
        self.extract_calls += 1
        self.extraction_catalog = concepts or []
        snippets = [span["text"] for span in spans]
        if self.invalid_extraction:
            snippets[-1] = "材料里没有的句子"
        content = make_content(
            [span["segment_id"] for span in spans], snippets, concept_ids=self.suggested_concepts,
        )
        if self.incorrect_model_offsets:
            content["fields"]["context"]["evidence"][0].update(start_char=1, end_char=2)
        return ExtractionOutput.model_validate({
            "candidates": [{
                "segment_ids": [span["segment_id"] for span in spans],
                "content": content,
            }]
        })

    def answer(self, query, evidence, config, *, cases, language):
        if not evidence:
            return ModelAnswer(
                answer="The published cases do not establish a reason.", evidence_fit="none",
                claims=[], next_step="Ask a student what happened the last time they stopped working.",
            )
        strategy = next(item for item in evidence if item["field"] == "strategy")
        return ModelAnswer(
            answer="相关案例提供了一种课堂策略。", evidence_fit="direct",
            claims=[AnswerClaim(
                text=strategy["quote"],
                evidence_ids=["invented"] if self.invalid_answer else [strategy["id"]],
            )],
            reflection_questions=["有何不同？"],
        )


@pytest.fixture()
def workflow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    engine = create_engine(f"sqlite:///{(tmp_path / 'practice.db').as_posix()}")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    practice = PracticeService(factory)
    model = ModelDouble()
    monkeypatch.setattr(routes, "practice", practice)
    monkeypatch.setattr(routes, "extraction", PracticeExtractionService(practice, model))
    monkeypatch.setattr(routes, "training", TrainingService(practice, model))
    monkeypatch.setattr(resource_routes, "service", ResearchResourceService(factory, tmp_path / "storage"))
    client = TestClient(app)
    yield client, factory, model
    engine.dispose()


def test_followup_scans_interviews_and_cites_the_original_record(workflow, monkeypatch):
    client, factory, model = workflow
    quote = "遇到课堂沉默时，我让每名学生先写一个想法，再两人交换。"
    with factory.begin() as session:
        for kind in ("analysis", "import"):
            session.add(CorpusDataset(
                id=f"educator-interviews-{kind}", name=kind, data_kind=kind, domain="education",
                file_name=f"interviews-{kind}.csv",
            ))
        session.add(CorpusDataset(id="other", name="Other", data_kind="import", domain="education"))
        session.flush()
        session.add_all([
            CorpusRecord(dataset_id="educator-interviews-analysis", text=quote),
            CorpusRecord(dataset_id="other", text="课堂沉默是课堂沉默课堂沉默课堂沉默。"),
            *[
                CorpusRecord(dataset_id="educator-interviews-import", text=f"我在学校的成长回忆共有 {index} 节。")
                for index in range(80)
            ],
            CorpusRecord(dataset_id="educator-interviews-import", text=quote),
        ])

    history = [{"question": "怎样了解课堂沉默？", "answer": "先观察哪些环节学生没有回应。"}]

    def expand(query, concepts, config, *, history):
        assert query == "下一步怎么试？"
        assert history[0]["question"] == "怎样了解课堂沉默？"
        return CaseQueryExpansion(search_phrases=["课堂沉默"])

    def reply(query, evidence, config, *, cases, language, history):
        assert not cases
        assert history[0]["answer"] == "先观察哪些环节学生没有回应。"
        assert [entry["quote"] for entry in evidence] == [quote]
        assert evidence[0]["source_file"] == "interviews-import.csv"
        return ModelAnswer(
            answer="可以先试两人交流。", evidence_fit="indirect",
            claims=[AnswerClaim(text="访谈记录了先独立想，再两人交流的做法。", evidence_ids=[evidence[0]["id"]])],
        )

    monkeypatch.setattr(model, "interpret_query", expand)
    monkeypatch.setattr(model, "answer", reply)
    response = client.post("/api/training/answers", json={"query": "下一步怎么试？", "history": history})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["matches"] == []
    assert data["claims"][0]["evidence"][0]["kind"] == "interview"
    assert data["lookup_trace"] == [
        {"action": "interview_scan", "count": 82}, {"action": "interview_context", "count": 1},
    ]


def import_source(client, name="样例甲", access="internal", lines=None):
    text = "\n\n".join(lines or [CONTEXT, PROBLEM, STRATEGY])
    response = client.post("/api/research-resources/import", files={
        "files": (name + ".txt", text.encode("utf-8"), "text/plain")
    }, data={
        "title": name, "fulltext_allowed": "true", "copyright_status": "authorized",
        "access_level": access, "source_url": "https://example.edu/source", "data_version": "2",
    })
    assert response.status_code == 200, response.text
    resource_id = response.json()["results"][0]["resource_id"]
    resource = client.get(f"/api/research-resources/{resource_id}").json()
    return resource_id, [item["id"] for item in resource["segments"]]


def make_content(segment_ids, snippets=None, *, title="讨论参与案例", concept_ids=None):
    values = snippets or [CONTEXT, PROBLEM, STRATEGY]
    return {
        "title": title, "actor_name": "𠮷老师", "applicability": "可组织小组任务",
        "fields": {
            field: {"state": "supported", "summary": quote, "evidence": [{"segment_id": segment, "quote": quote}]}
            for field, segment, quote in zip(("context", "problem", "strategy"), segment_ids, values)
        },
        "concept_ids": concept_ids or [],
    }


def create_case(client, resource_id, segment_ids, **options):
    response = client.post("/api/practice/cases", json={
        "resource_id": resource_id, "segment_ids": segment_ids,
        "content": make_content(segment_ids, **options), "request_id": str(uuid4()),
    })
    assert response.status_code == 201, response.text
    return response.json()


def review_and_publish(client, document, expected_status=200):
    case_id = document["case_id"]
    base = f"/api/practice/cases/{case_id}"
    submitted = client.post(base + "/submit", json={"expected_version": document["version"]})
    assert submitted.status_code == 200, submitted.text
    response = client.post(base + "/publish", json={
        "expected_version": submitted.json()["version"], "reviewer": "本地测试",
        "training_allowed": True, "confirmed": True,
    })
    assert response.status_code == expected_status, response.text
    return response.json()


def test_manual_case_lifecycle_versions_and_citation_visibility(workflow):
    client, _, _ = workflow
    resource_id, segment_ids = import_source(client)
    draft = create_case(client, resource_id, segment_ids)
    case_id = draft["case_id"]
    learner = f"/api/training/cases/{case_id}"
    assert client.get(learner).status_code == 404
    assert client.get("/api/training/cases").json() == []

    first = review_and_publish(client, draft)
    published = client.get(learner).json()
    assert published["revision"] == 1
    assert "spans" not in published["source"]
    assert "reviewer" not in published
    evidence = published["fields"]["context"]["evidence"][0]
    assert (evidence["start_char"], evidence["end_char"]) == (0, len(CONTEXT))
    citation = f"{learner}/evidence/{evidence['id']}?revision=1"
    located = client.get(citation).json()
    assert located["quote"] == CONTEXT
    assert located["source"]["data_version"] == "2"

    draft_route = f"/api/practice/cases/{case_id}/draft"
    new_request = {
        "expected_version": first["version"],
        "content": make_content(segment_ids, title="新标题"),
    }
    response = client.put(draft_route, json=new_request)
    assert response.status_code == 200, response.text
    second_draft = response.json()
    assert client.put(draft_route, json=new_request).status_code == 409
    assert client.get(learner).json()["title"] == "讨论参与案例"
    assert client.get(learner + "?revision=2").status_code == 404

    second = review_and_publish(client, second_draft)
    assert client.get(learner).json()["title"] == "新标题"
    assert client.get(citation).status_code == 200
    response = client.post(f"/api/practice/cases/{case_id}/withdraw", json={
        "expected_version": second["version"],
    })
    assert response.status_code == 200
    assert client.get(learner).status_code == 404
    assert client.get(citation).status_code == 404
    assert client.get(learner + "/graph").status_code == 404


def test_publish_requires_core_evidence_and_source_sharing_permission(workflow):
    client, _, _ = workflow
    resource_id, segment_ids = import_source(client, access="restricted")
    document = create_case(client, resource_id, segment_ids)
    assert "版权状态" in review_and_publish(client, document, expected_status=422)["detail"]

    resource_id, segment_ids = import_source(client, "样例乙", lines=[CONTEXT, PROBLEM, STRATEGY + "活动随后结束。"])
    payload = {
        "resource_id": resource_id, "segment_ids": segment_ids,
        "content": {"title": "缺少字段"},
    }
    draft = client.post("/api/practice/cases", json=payload).json()
    detail = review_and_publish(client, draft, expected_status=422)["detail"]
    assert "教育情境、实际问题、行动策略" in detail

    payload["content"] = make_content(segment_ids, ["伪造原文", PROBLEM, STRATEGY])
    assert client.post("/api/practice/cases", json=payload).status_code == 422


def test_graph_search_answer_and_permissions_use_published_cases(workflow):
    client, factory, model = workflow
    concept = client.post("/api/practice/concepts", json={
        "kind": "problem", "label": "学生参与不均", "aliases": ["发言机会不均"]
    }).json()
    first_id, first_segments = import_source(client)
    new_strategy = "教师先让每人独立思考，再安排轮流发言。"
    second_id, second_segments = import_source(client, "样例乙", lines=[CONTEXT, PROBLEM, new_strategy])
    first = create_case(client, first_id, first_segments, concept_ids=[concept["id"]])
    second = create_case(client, second_id, second_segments, title="轮流发言", concept_ids=[concept["id"]],
                         snippets=[CONTEXT, PROBLEM, new_strategy])
    first = review_and_publish(client, first)
    graph_url = f'/api/training/cases/{first["case_id"]}/graph'
    assert len([node for node in client.get(graph_url).json()["nodes"] if node["kind"] == "case"]) == 1
    second = review_and_publish(client, second)
    graph = client.get(graph_url).json()
    assert {node["case_id"] for node in graph["nodes"] if node["kind"] == "case"} == {
        first["case_id"], second["case_id"]
    }

    query = {"query": "发言机会不均"}
    search = client.post("/api/training/cases/search", json=query).json()
    assert len(search) == 2
    assert search[0]["matched_concepts"] == ["学生参与不均"]
    answer = client.post("/api/training/answers", json=query).json()
    assert answer["mode"] == "grounded"
    assert answer["claims"][0]["evidence"][0]["field"] == "strategy"

    model.invalid_answer = True
    fallback = client.post("/api/training/answers", json=query).json()
    assert fallback["mode"] == "evidence"
    assert all(claim["evidence"][0]["id"] != "invented" for claim in fallback["claims"])

    case_ids = [first["case_id"], second["case_id"]]
    metrics = client.post("/api/practice/evaluations", json={
        "top_k": 2, "cases": [{"query": query["query"], "expected_case_ids": case_ids}]
    }).json()
    assert metrics["hit_rate_at_k"] == 1 and metrics["mean_reciprocal_rank"] == 1

    with factory() as session:
        session.get(ResearchResource, first_id).access_level = "restricted"
        session.commit()
    assert client.get(graph_url).status_code == 404
    results = client.post("/api/training/cases/search", json=query).json()
    assert [item["id"] for item in results] == [second["case_id"]]
    assert client.post("/api/training/answers", json={"query": "火山熔岩"}).json()["mode"] == "insufficient"


def test_semantic_search_recovers_paraphrase_and_answer_reuses_matches(workflow):
    client, _, model = workflow
    concept = client.post("/api/practice/concepts", json={
        "kind": "problem", "label": "学生参与不均", "aliases": ["发言机会不均"]
    }).json()
    private_concept = client.post("/api/practice/concepts", json={
        "kind": "problem", "label": "仅供草稿复核"
    }).json()
    resource_id, segments = import_source(client)
    draft = create_case(client, resource_id, segments, concept_ids=[concept["id"]])
    published = review_and_publish(client, draft)
    create_case(client, resource_id, segments, concept_ids=[private_concept["id"]])

    natural_question = "课堂交流总是那几个人开口，怎样让其他孩子也愿意表达"
    model.expansion = CaseQueryExpansion(concept_ids=[concept["id"], private_concept["id"]])
    keyword_hits = client.post("/api/training/cases/search", json={"query": "发言机会不均"}).json()
    assert keyword_hits[0]["match_method"] == "lexical"
    assert not model.query_calls

    hits = client.post("/api/training/cases/search", json={"query": natural_question}).json()
    assert [case["id"] for case in hits] == [published["case_id"]]
    assert hits[0]["match_method"] == "semantic"
    assert hits[0]["matched_concepts"] == ["学生参与不均"]
    assert [item["id"] for item in model.query_calls[0][1]] == [concept["id"]]

    answer = client.post("/api/training/answers", json={"query": natural_question}).json()
    assert answer["matches"] == hits
    assert answer["mode"] == "grounded"
    assert answer["claims"][0]["evidence"][0]["case_id"] == published["case_id"]
    assert len(model.query_calls) == 2


def test_semantic_rewrite_finds_untagged_case_and_preserves_lexical_fallback(workflow):
    client, _, model = workflow
    resource_id, segments = import_source(client)
    published = review_and_publish(client, create_case(client, resource_id, segments))
    model.expansion = CaseQueryExpansion(search_phrases=["小组讨论"])

    query = {"query": "课堂交流总是那几个人开口，怎样让其他孩子也愿意表达"}
    hits = client.post("/api/training/cases/search", json=query).json()
    assert [case["id"] for case in hits] == [published["case_id"]]
    assert hits[0]["match_method"] == "semantic"

    model.interpretation_fails = True
    assert client.post("/api/training/cases/search", json=query).json() == []
    lexical_query = {"query": "两名学生发言"}
    fallback = client.post("/api/training/cases/search", json=lexical_query).json()
    assert fallback[0]["id"] == published["case_id"]
    assert fallback[0]["match_method"] == "lexical"


def test_answer_keeps_a_useful_next_step_when_the_library_has_no_evidence(workflow):
    client, _, _ = workflow
    result = client.post("/api/training/answers", json={"query": "why the students don't like study?"}).json()
    assert result["language"] == "en"
    assert result["mode"] == "insufficient"
    assert result["evidence_fit"] == "none"
    assert result["claims"] == []
    assert result["answer"]
    assert result["next_step"]


def test_indirect_evidence_can_be_shown_with_a_qualified_answer(workflow, monkeypatch):
    client, _, model = workflow
    resource_id, segments = import_source(client)
    published = review_and_publish(client, create_case(client, resource_id, segments))
    model.expansion = CaseQueryExpansion(search_phrases=["小组讨论"])

    def answer(query, evidence, config, *, cases, language):
        assert query == "why the students don't like study?"
        assert language == "en"
        assert cases[0]["case_id"] == published["case_id"]
        assert cases[0]["fields"]["outcome"]["state"] == "not_stated"
        problem = next(item for item in evidence if item["field"] == "problem")
        return ModelAnswer(
            answer="The case shows low participation in a discussion. The students' reasons are still unclear.",
            evidence_fit="indirect",
            claims=[AnswerClaim(text="Only two students spoke.", evidence_ids=[problem["id"]])],
            next_step="Ask a few students privately what happened when they last stopped working.",
            clarifying_question="Do they also avoid independent work, or mainly stay quiet in discussions?",
        )

    monkeypatch.setattr(model, "answer", answer)
    response = client.post("/api/training/answers", json={"query": "why the students don't like study?"})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["language"] == "en"
    assert result["evidence_fit"] == "indirect"
    assert "reasons are still unclear" in result["answer"]
    assert result["next_step"] and result["clarifying_question"]
    assert [quote["case_id"] for claim in result["claims"] for quote in claim["evidence"]] == [published["case_id"]]


def test_search_finds_source_quotes_beyond_the_first_catalog_page(workflow):
    client, _, _ = workflow
    strategy = "老师将彩色河流模型交给各组做示范。"
    resource_id, segments = import_source(client, lines=[CONTEXT, PROBLEM, strategy])
    content = make_content(segments, [CONTEXT, PROBLEM, strategy])
    content["fields"]["strategy"]["summary"] = "教师使用教具展示做法。"
    draft = client.post("/api/practice/cases", json={
        "resource_id": resource_id, "segment_ids": segments, "content": content,
    }).json()
    published = review_and_publish(client, draft)
    later_id, later_segments = import_source(client, "后来发布的案例")
    for index in range(12):
        review_and_publish(client, create_case(client, later_id, later_segments, title=f"讨论案例 {index}"))

    first_page = client.get("/api/training/cases", params={"limit": 12}).json()
    assert published["case_id"] not in [card["id"] for card in first_page]
    result = client.post("/api/training/cases/search", json={"query": "彩色河流模型"}).json()
    assert [card["id"] for card in result] == [published["case_id"]]


def test_english_question_retries_a_chinese_model_reply(monkeypatch):
    model = practice_engine.PracticeModel()
    answers = iter([
        ModelAnswer(answer="现有证据无法说明原因。", evidence_fit="none", claims=[]),
        ModelAnswer(answer="The cases do not establish a cause.", evidence_fit="none", claims=[]),
    ])
    prompts = []

    def complete(prompt, data, schema, config):
        prompts.append(prompt)
        return next(answers)

    monkeypatch.setattr(model, "_complete", complete)
    reply = model.answer("Why do some students avoid studying?", [], {}, cases=[], language="en")
    assert reply.answer == "The cases do not establish a cause."
    assert len(prompts) == 2
    assert prompts[0].startswith("Use English")


def test_extraction_persists_failure_retries_and_accepts_candidate_once(workflow):
    client, _, model = workflow
    resource_id, segment_ids = import_source(client)
    concept = client.post("/api/practice/concepts", json={
        "kind": "problem", "label": "学生参与不均"
    }).json()
    model.suggested_concepts = [concept["id"], "unknown-concept"]
    selection = {"resource_id": resource_id, "segment_ids": segment_ids}
    model.invalid_extraction = True
    run = client.post("/api/practice/extractions", json=selection).json()
    url = f'/api/practice/extractions/{run["id"]}'
    failed = client.get(url).json()
    assert failed["status"] == "failed"
    assert "引文" in failed["error"]
    assert model.extract_calls == 1
    assert [item["id"] for item in model.extraction_catalog] == [concept["id"]]
    assert client.post("/api/practice/extractions", json=selection).json()["id"] == run["id"]
    client.post("/api/practice/concepts", json={"kind": "problem", "label": "后来新增概念"})

    model.invalid_extraction = False
    model.incorrect_model_offsets = True
    assert client.post(url + "/retry").status_code == 202
    succeeded = client.get(url).json()
    assert succeeded["status"] == "succeeded" and succeeded["attempt"] == 2
    assert len(succeeded["candidates"]) == 1
    assert [item["id"] for item in model.extraction_catalog] == [concept["id"]]
    assert succeeded["candidates"][0]["content"]["concept_ids"] == [concept["id"]]
    quote = succeeded["candidates"][0]["content"]["fields"]["context"]["evidence"][0]
    assert (quote["start_char"], quote["end_char"]) == (0, len(CONTEXT))
    assert model.extract_calls == 2

    accept = url + "/candidates/0/accept"
    first = client.post(accept).json()
    second = client.post(accept).json()
    assert first["case_id"] == second["case_id"]
    assert first["published_revision"] is None
    assert [item["id"] for item in first["concepts"]] == [concept["id"]]
    assert "extraction_concepts" not in first["source"]
    assert client.get("/api/training/cases").json() == []


def test_relocation_requires_one_literal_match_for_wrong_offsets():
    source = "老师请同学提问。老师请同学提问。"
    with pytest.raises(ValueError, match="重复位置不明确"):
        resolve_quote(source, "同学提问", 0, 2, relocate_invalid_offsets=True)
    with pytest.raises(ValueError, match="字符范围不一致"):
        resolve_quote("老师请同学提问。", "同学提问", 0, 2)


def test_model_client_sends_reviewable_inputs_and_detects_endpoint_change(monkeypatch):
    runtime = SimpleNamespace(
        enabled=True, configured=True, profile_id="test", provider="local",
        model_name="local-test", base_url="http://model.test/v1", api_key="test-key",
    )
    profile = SimpleNamespace(get_runtime_config=lambda: runtime)
    monkeypatch.setattr(practice_engine, "get_foundation_profile_service", lambda: profile)
    seen = []

    def complete(request):
        seen.append(request.url.path)
        body = json.loads(request.content)
        assert body["model"] == runtime.model_name
        assert request.headers["Authorization"] == "Bearer test-key"
        assert json.loads(body["messages"][1]["content"]) == {"spans": [{"segment_id": "example", "text": CONTEXT}]}
        return httpx.Response(200, json={"choices": [{
            "message": {"content": '{"candidates":[]}'}, "finish_reason": "stop",
        }]})

    client = httpx.Client
    transport = httpx.MockTransport(complete)
    monkeypatch.setattr(practice_engine.httpx, "Client", lambda **kwargs: client(transport=transport, **kwargs))
    model = practice_engine.PracticeModel()
    config = model.configuration()
    assert "api_key" not in config and "base_url" not in config
    assert model.extract([{"segment_id": "example", "text": CONTEXT}], config).candidates == []
    runtime.base_url = "http://other-model.test/v1"
    with pytest.raises(ValueError, match="模型配置已经变化"):
        model.extract([], config)
    assert seen == ["/v1/chat/completions"]


def test_deepseek_query_interpretation_requests_json_output(monkeypatch):
    runtime = SimpleNamespace(
        enabled=True, configured=True, profile_id="deepseek-chat", provider="deepseek",
        model_name="deepseek-flash", base_url="https://api.deepseek.com/v1", api_key="test-key",
    )
    profile = SimpleNamespace(get_runtime_config=lambda: runtime)
    monkeypatch.setattr(practice_engine, "get_foundation_profile_service", lambda: profile)

    def complete(request):
        body = json.loads(request.content)
        assert request.url.path == "/v1/chat/completions"
        assert body["response_format"] == {"type": "json_object"}
        assert body["thinking"] == {"type": "disabled"}
        assert json.loads(body["messages"][1]["content"]) == {"query": "没人接话", "concepts": [], "history": []}
        return httpx.Response(200, json={"choices": [{
            "message": {"content": '{"concept_ids":[],"search_phrases":["课堂讨论"]}'},
            "finish_reason": "stop",
        }]})

    client = httpx.Client
    transport = httpx.MockTransport(complete)
    monkeypatch.setattr(practice_engine.httpx, "Client", lambda **kwargs: client(transport=transport, **kwargs))
    model = practice_engine.PracticeModel()
    assert model.interpret_query("没人接话", [], model.configuration()).search_phrases == ["课堂讨论"]


def test_deepseek_uses_case_graph_and_original_evidence(workflow, monkeypatch):
    client, _, _ = workflow
    concept = client.post("/api/practice/concepts", json={
        "kind": "problem", "label": "学生参与不均"
    }).json()
    source_id, segments = import_source(client)
    primary = review_and_publish(client, create_case(
        client, source_id, segments, title="同伴发言分配", concept_ids=[concept["id"]],
    ))
    alternative = "教师先让每个人写下一个观点，再按顺序分享。"
    source_id, segments = import_source(client, "样例乙", lines=[CONTEXT, PROBLEM, alternative])
    related = review_and_publish(client, create_case(
        client, source_id, segments, title="先写后说", concept_ids=[concept["id"]],
        snippets=[CONTEXT, PROBLEM, alternative],
    ))
    draft = create_case(client, source_id, segments, title="只在研究端可见",
                        concept_ids=[concept["id"]], snippets=[CONTEXT, PROBLEM, alternative])

    runtime = SimpleNamespace(
        enabled=True, configured=True, profile_id="deepseek-chat", provider="deepseek",
        model_name="deepseek-flash", base_url="https://api.deepseek.com/v1", api_key="test-key",
    )
    profile = SimpleNamespace(get_runtime_config=lambda: runtime)
    monkeypatch.setattr(practice_engine, "get_foundation_profile_service", lambda: profile)
    monkeypatch.setattr(routes.training, "model", practice_engine.PracticeModel())
    requests = []

    def tool_call(call_id, name, arguments):
        return {"id": call_id, "type": "function", "function": {
            "name": name, "arguments": json.dumps(arguments, ensure_ascii=False),
        }}

    def tool_result(body, call_id):
        message = next(item for item in body["messages"] if item.get("tool_call_id") == call_id)
        return json.loads(message["content"])

    def chat_reply(content, calls=None):
        message = {"role": "assistant", "content": content}
        if calls is not None:
            message["tool_calls"] = calls
        return httpx.Response(200, json={"choices": [{
            "message": message, "finish_reason": "tool_calls" if calls else "stop",
        }]})

    def complete(request):
        body = json.loads(request.content)
        requests.append(body)
        if len(requests) == 1:
            assert {tool["function"]["name"] for tool in body["tools"]} == {
                "browse_published_cases", "search_published_cases", "find_related_cases", "get_case_evidence", "search_interviews",
            }
            catalog = json.loads(body["messages"][1]["content"])["case_catalog"]["cases"]
            assert {card["id"] for card in catalog} == {primary["case_id"], related["case_id"]}
            return chat_reply(None, [tool_call("search", "search_published_cases", {
                "queries": ["同伴发言分配"], "limit": 1,
            })])
        if len(requests) == 2:
            cards = tool_result(body, "search")["cases"]
            assert [item["id"] for item in cards] == [primary["case_id"]]
            return chat_reply(None, [
                tool_call("graph", "find_related_cases", {"case_id": cards[0]["id"], "revision": cards[0]["revision"]}),
                tool_call("draft", "get_case_evidence", {"case_id": draft["case_id"], "revision": draft["revision"]}),
            ])
        if len(requests) == 3:
            cards = tool_result(body, "graph")["cases"]
            assert [item["id"] for item in cards] == [related["case_id"]]
            assert "error" in tool_result(body, "draft")
            return chat_reply(None, [tool_call("evidence", "get_case_evidence", {
                "case_id": cards[0]["id"], "revision": cards[0]["revision"],
            })])
        if len(requests) == 4:
            citations = tool_result(body, "evidence")["citations"]
            strategy = next(entry for entry in citations if entry["field"] == "strategy")
            assert strategy["quote"] == alternative and strategy["source_title"] == "样例乙"
            return chat_reply("")
        assert len(requests) == 5 and body["response_format"] == {"type": "json_object"}
        context = json.loads(body["messages"][1]["content"])
        assert [item["case_id"] for item in context["cases"]] == [related["case_id"], primary["case_id"]]
        assert context["cases"][0]["fields"]["strategy"]["summary"] == alternative
        evidence = context["evidence"]
        strategy = next(entry for entry in evidence if entry["field"] == "strategy")
        return chat_reply(json.dumps({
            "answer": "同类案例提供了一种让更多学生表达的做法。",
            "evidence_fit": "direct",
            "claims": [{"text": strategy["quote"], "evidence_ids": [strategy["id"]]}],
        }))

    http_client = httpx.Client
    transport = httpx.MockTransport(complete)
    monkeypatch.setattr(practice_engine.httpx, "Client", lambda **kw: http_client(transport=transport, **kw))
    response = client.post("/api/training/answers", json={"query": "怎样让更多孩子开口，想看看别的做法？"})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["mode"] == "grounded"
    assert [step["action"] for step in data["lookup_trace"]] == ["catalog", "search", "graph", "evidence", "context"]
    assert data["matches"][0]["match_method"] == "graph"
    citation = data["claims"][0]["evidence"][0]
    assert citation["case_id"] == related["case_id"]
    assert citation["quote"] == alternative
