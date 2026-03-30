import pytest
from fastapi.testclient import TestClient

from app.api.routes.analysis import (
    dataset_service,
    foundation_profile_service,
    public_data_service,
    reference_library_service,
    service as route_service,
)
from app.main import app
from app.services.analysis_service import AnalysisService


client = TestClient(app)


@pytest.fixture(autouse=True)
def stub_route_explanations(monkeypatch):
    monkeypatch.setattr(
        route_service,
        "_generate_explanation",
        lambda **kwargs: kwargs["fallback"],
    )


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_single_analysis() -> None:
    response = client.post(
        "/api/analyze",
        json={"text": "我会把课堂反馈和项目实践都放进教学设计里，让学生在真实任务中成长。"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["category"] == "职业人格"
    assert payload["level"] in {"初显现", "中显现", "高显现"}
    assert payload["needs_attention"] is True
    assert "课堂" in payload["keywords"]
    assert len(payload["score_breakdown"]) >= 2


def test_batch_analysis() -> None:
    response = client.post(
        "/api/analyze/batch",
        json={
            "texts": [
                "教育的本质若要用一个字概括，就是爱，教师的眼中才能真正看见学生。",
                "未来教育最大的挑战，是在人工智能进入课堂后依然保留教育的人文温度。",
                "今天整理了一下教学资料。",
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total"] == 3
    assert len(payload["summary"]["category_distribution"]) >= 1
    assert len(payload["summary"]["level_distribution"]) >= 1
    assert "wordcloud_keywords" in payload["summary"]
    assert "avg_score" in payload["summary"]
    assert len(payload["results"]) == 3


def test_generate_targeted_explanation(monkeypatch) -> None:
    monkeypatch.setattr(
        foundation_profile_service,
        "get_runtime_config",
        lambda: type(
            "Runtime",
            (),
            {
                "profile_id": "foundation-disabled",
                "label": "关闭强模型",
                "provider": "none",
                "base_url": "",
                "model_name": "",
                "api_key": "",
                "enabled": False,
                "configured": False,
            },
        )(),
    )

    response = client.post(
        "/api/explanations/generate",
        json={
            "text": "我想在课堂上多给学生留一点讨论和反馈的空间。",
            "category": "职业人格",
            "level": "中显现",
            "keywords": ["课堂", "学生", "反馈"],
            "rule_reason": "文本最集中地体现了“职业人格”。",
            "fallback": "",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "解释" not in payload["explanation"]
    assert "职业人格" in payload["explanation"]


def test_list_reference_library() -> None:
    response = client.get("/api/reference-library")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_name"] == "教育家三重人格底库"
    assert len(payload["dimensions"]) == 3
    assert payload["dimensions"][0]["sample_quotes"]


def test_list_foundation_model_profiles() -> None:
    response = client.get("/api/foundation-model/profiles")
    assert response.status_code == 200
    payload = response.json()
    assert any(item["id"] == "ollama-qwen2.5" for item in payload)
    assert any(item["id"] == "ollama-deepseek-r1" for item in payload)
    assert any(item["id"] == "deepseek-chat" for item in payload)


def test_activate_foundation_model_profile(monkeypatch) -> None:
    monkeypatch.setattr(foundation_profile_service, "activate_profile", lambda profile_id: None)
    monkeypatch.setattr(
        foundation_profile_service,
        "get_runtime_config",
        lambda: type(
            "Runtime",
            (),
            {
                "profile_id": "deepseek-chat",
                "label": "DeepSeek Chat",
                "provider": "deepseek",
                "base_url": "https://api.deepseek.com/v1",
                "model_name": "deepseek-chat",
                "api_key": "secret",
                "enabled": True,
                "configured": True,
            },
        )(),
    )

    response = client.post("/api/foundation-model/activate", json={"profile_id": "deepseek-chat"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_foundation_profile_id"] == "deepseek-chat"
    assert payload["foundation_model_name"] == "deepseek-chat"


def test_list_public_sources() -> None:
    response = client.get("/api/public-sources")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 1
    assert "id" in payload[0]
    assert "feed_url" in payload[0]


def test_fetch_public_source(monkeypatch) -> None:
    def fake_fetch_and_analyze(source_id: str, limit: int = 8):
        return {
            "source": {
                "id": source_id,
                "name": "测试源",
                "description": "测试描述",
                "feed_url": "https://example.com/feed.xml",
            },
            "fetched_count": 2,
            "texts": ["我想让课堂更重视反馈。", "未来教育需要更多创新尝试。"],
            "analysis": {
                "summary": {
                    "total": 2,
                    "category_distribution": {"职业人格": 1, "自然人格": 1},
                    "level_distribution": {"中显现": 1, "高显现": 1},
                    "top_keywords": [{"keyword": "课堂", "count": 1}],
                    "wordcloud_keywords": [{"keyword": "课堂", "count": 1}],
                    "attention_count": 2,
                    "high_risk_texts": [],
                    "avg_score": 0.72,
                },
                "results": [
                    {
                        "text": "我想让课堂更重视反馈。",
                        "category": "职业人格",
                        "level": "中显现",
                        "score": 0.66,
                        "keywords": ["课堂", "反馈"],
                        "rule_reason": "测试规则说明",
                        "llm_explanation": "测试解释",
                        "needs_attention": True,
                        "dominant_dimension_id": "professional_personality",
                        "dimension_scores": [],
                        "indicator_scores": [],
                        "reference_quotes": [],
                    },
                    {
                        "text": "未来教育需要更多创新尝试。",
                        "category": "自然人格",
                        "level": "高显现",
                        "score": 0.79,
                        "keywords": ["未来", "创新"],
                        "rule_reason": "测试规则说明",
                        "llm_explanation": "测试解释",
                        "needs_attention": True,
                        "dominant_dimension_id": "natural_personality",
                        "dimension_scores": [],
                        "indicator_scores": [],
                        "reference_quotes": [],
                    },
                ],
            },
        }

    monkeypatch.setattr(public_data_service, "fetch_and_analyze", fake_fetch_and_analyze)

    response = client.post("/api/public-sources/fetch", json={"source_id": "xidian-tieba", "limit": 2})

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"]["id"] == "xidian-tieba"
    assert payload["fetched_count"] == 2
    assert payload["analysis"]["summary"]["total"] == 2


def test_get_default_dataset(monkeypatch) -> None:
    def fake_get_default_dataset_analysis():
        return {
            "summary": {
                "total": 2,
                "category_distribution": {"职业人格": 1, "道德人格": 1},
                "level_distribution": {"中显现": 1, "高显现": 1},
                "top_keywords": [{"keyword": "学生", "count": 1}],
                "wordcloud_keywords": [{"keyword": "课堂", "count": 2}],
                "attention_count": 2,
                "high_risk_texts": [],
                "avg_score": 0.71,
            },
            "results": [
                {
                    "text": "我希望先理解学生，再设计课堂节奏。",
                    "category": "职业人格",
                    "level": "中显现",
                    "score": 0.66,
                    "keywords": ["学生", "理解", "课堂"],
                    "rule_reason": "命中共情育人线索。",
                    "llm_explanation": "文本与共情育人维度较接近。",
                    "needs_attention": True,
                    "dominant_dimension_id": "professional_personality",
                    "dimension_scores": [],
                    "indicator_scores": [],
                    "reference_quotes": [],
                },
                {
                    "text": "未来教育要处理技术与温度的平衡。",
                    "category": "道德人格",
                    "level": "高显现",
                    "score": 0.76,
                    "keywords": ["未来", "技术"],
                    "rule_reason": "命中创新引领线索。",
                    "llm_explanation": "文本与创新引领维度较接近。",
                    "needs_attention": True,
                    "dominant_dimension_id": "moral_personality",
                    "dimension_scores": [],
                    "indicator_scores": [],
                    "reference_quotes": [],
                },
            ],
        }

    monkeypatch.setattr(dataset_service, "get_default_dataset_analysis", fake_get_default_dataset_analysis)

    response = client.get("/api/datasets/default")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total"] == 2
    assert payload["summary"]["wordcloud_keywords"][0]["keyword"] == "课堂"
    assert payload["results"][0]["category"] == "职业人格"


def test_list_datasets(monkeypatch) -> None:
    monkeypatch.setattr(
        dataset_service,
        "list_datasets",
        lambda: [
            {
                "id": "educator-interviews-import",
                "name": "教育家型教师访谈底库",
                "description": "测试数据集",
                "file_name": "educator_interviews_import.csv",
                "data_kind": "import",
                "record_count": 669,
                "attention_count": 120,
                "updated_at": "2026-03-29 01:22",
                "is_default": True,
            }
        ],
    )

    response = client.get("/api/datasets")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["id"] == "educator-interviews-import"
    assert payload[0]["record_count"] == 669


def test_get_dataset_by_id(monkeypatch) -> None:
    def fake_get_dataset_analysis(dataset_id: str):
        assert dataset_id == "demo-texts"
        return {
            "summary": {
                "total": 1,
                "category_distribution": {"职业人格": 1},
                "level_distribution": {"中显现": 1},
                "top_keywords": [],
                "wordcloud_keywords": [{"keyword": "课堂", "count": 1}],
                "attention_count": 1,
                "high_risk_texts": [],
                "avg_score": 0.63,
            },
            "results": [
                {
                    "text": "今天课堂状态不错，也有及时反馈。",
                    "category": "职业人格",
                    "level": "中显现",
                    "score": 0.63,
                    "keywords": ["课堂", "反馈"],
                    "rule_reason": "命中实践教学线索。",
                    "llm_explanation": "文本整体更接近实践教学维度。",
                    "needs_attention": True,
                    "dominant_dimension_id": "professional_personality",
                    "dimension_scores": [],
                    "indicator_scores": [],
                    "reference_quotes": [],
                }
            ],
        }

    monkeypatch.setattr(dataset_service, "get_dataset_analysis", fake_get_dataset_analysis)

    response = client.get("/api/datasets/demo-texts")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total"] == 1
    assert payload["results"][0]["text"] == "今天课堂状态不错，也有及时反馈。"


def test_analysis_service_can_use_llm() -> None:
    class FakeLLM:
        def generate_explanation(self, **kwargs) -> str | None:
            return "这是来自大模型的解释。"

    class FakeFoundationModel:
        def generate_explanation(self, **kwargs) -> None:
            return None

    service = AnalysisService(
        foundation_model_engine=FakeFoundationModel(),
        llm_engine=FakeLLM(),
    )

    result = service.analyze_text(
        payload=type("Payload", (), {"text": "我更想先听懂学生为什么沉默，再决定怎么推进课堂。"})()
    )

    assert result.category == "职业人格"
    assert result.llm_explanation == "这是来自大模型的解释。"
