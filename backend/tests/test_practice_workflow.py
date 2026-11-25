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
from app.db.research_models import ResearchResource
from app.engines.practice import engine as practice_engine
from app.main import app
from app.schemas.practice import AnswerClaim, ExtractionOutput, ModelAnswer
from app.services.practice_extraction_service import PracticeExtractionService
from app.services.practice_service import PracticeService
from app.services.research_resource_service import ResearchResourceService
from app.services.training_service import TrainingService

CONTEXT = "𠮷老师负责组织小组讨论。"
PROBLEM = "小组讨论时只有两名学生发言。"
STRATEGY = "老师请每组轮流安排一名记录员汇报。"


class ModelDouble:
    def __init__(self):
        self.extract_calls = 0
        self.invalid_extraction = False
        self.invalid_answer = False

    def configuration(self):
        return {"profile_id": "test", "model": "test-model"}

    def extract(self, spans, config):
        self.extract_calls += 1
        snippets = [span["text"] for span in spans]
        if self.invalid_extraction:
            snippets[-1] = "材料里没有的句子"
        return ExtractionOutput.model_validate({
            "candidates": [{
                "segment_ids": [span["segment_id"] for span in spans],
                "content": make_content([span["segment_id"] for span in spans], snippets),
            }]
        })

    def answer(self, query, evidence, config):
        strategy = next(item for item in evidence if item["field"] == "strategy")
        return ModelAnswer(
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


def test_extraction_persists_failure_retries_and_accepts_candidate_once(workflow):
    client, _, model = workflow
    resource_id, segment_ids = import_source(client)
    selection = {"resource_id": resource_id, "segment_ids": segment_ids}
    model.invalid_extraction = True
    run = client.post("/api/practice/extractions", json=selection).json()
    url = f'/api/practice/extractions/{run["id"]}'
    failed = client.get(url).json()
    assert failed["status"] == "failed"
    assert "引文" in failed["error"]
    assert model.extract_calls == 1

    model.invalid_extraction = False
    assert client.post(url + "/retry").status_code == 202
    succeeded = client.get(url).json()
    assert succeeded["status"] == "succeeded" and succeeded["attempt"] == 2
    assert len(succeeded["candidates"]) == 1
    again = client.post("/api/practice/extractions", json=selection).json()
    assert again["id"] == run["id"]
    assert model.extract_calls == 2

    accept = url + "/candidates/0/accept"
    first = client.post(accept).json()
    second = client.post(accept).json()
    assert first["case_id"] == second["case_id"]
    assert first["published_revision"] is None
    assert client.get("/api/training/cases").json() == []


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
