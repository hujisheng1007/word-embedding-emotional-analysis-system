from fastapi.testclient import TestClient

from app.api.routes.analysis import dataset_service, foundation_profile_service, public_data_service
from app.engines.small_model.engine import SmallModelPrediction
from app.main import app
from app.services.analysis_service import AnalysisService


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_single_analysis() -> None:
    response = client.post(
        "/api/analyze",
        json={"text": "我感觉自己不想活了，什么都没有意义。", "mode": "hybrid"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["category"] == "心理风险"
    assert payload["level"] == "高"
    assert payload["needs_attention"] is True
    assert "不想活了" in payload["keywords"]
    assert len(payload["score_breakdown"]) >= 2


def test_batch_analysis() -> None:
    response = client.post(
        "/api/analyze/batch",
        json={
            "texts": [
                "我感觉自己不想活了，什么都没有意义。",
                "这个学校处理投诉的方式太离谱了，我准备发帖曝光。",
                "今天课堂氛围不错，整体比较顺利。",
            ],
            "mode": "hybrid",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total"] == 3
    assert payload["summary"]["attention_count"] == 2
    assert payload["summary"]["category_distribution"]["心理风险"] == 1
    assert payload["summary"]["category_distribution"]["舆情风险"] == 1
    assert "wordcloud_keywords" in payload["summary"]
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
            "text": "求助一下学长学姐，西安军械修理厂怎么样。",
            "category": "正常文本",
            "level": "正常",
            "keywords": [],
            "rule_reason": "未命中明显风险规则。",
            "fallback": "当前文本整体为日常表达。",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "解释" not in payload["explanation"]
    assert "西安军械修理厂" in payload["explanation"] or "日常求助" in payload["explanation"]


def test_list_foundation_model_profiles() -> None:
    response = client.get("/api/foundation-model/profiles")
    assert response.status_code == 200
    payload = response.json()
    assert any(item["id"] == "ollama-qwen2.5" for item in payload)
    assert any(item["id"] == "ollama-deepseek-r1" for item in payload)
    assert any(item["id"] == "deepseek-chat" for item in payload)


def test_activate_foundation_model_profile(monkeypatch) -> None:
    monkeypatch.setattr(
        foundation_profile_service,
        "activate_profile",
        lambda profile_id: None,
    )
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
    assert any(item["id"] == "xidian-tieba" for item in payload)


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
            "texts": ["学校投诉处理太慢了，我要曝光。", "我感觉自己不想活了。"],
            "analysis": {
                "summary": {
                    "total": 2,
                    "category_distribution": {"舆情风险": 1, "心理风险": 1},
                    "level_distribution": {"中": 1, "高": 1},
                    "top_keywords": [{"keyword": "学校", "count": 1}],
                    "wordcloud_keywords": [{"keyword": "学校", "count": 1}],
                    "attention_count": 2,
                    "high_risk_texts": [],
                },
                "results": [
                    {
                        "text": "学校投诉处理太慢了，我要曝光。",
                        "category": "舆情风险",
                        "level": "中",
                        "score": 0.76,
                        "keywords": ["学校", "投诉", "曝光"],
                        "rule_reason": "测试规则说明",
                        "llm_explanation": "测试解释",
                        "needs_attention": True,
                    },
                    {
                        "text": "我感觉自己不想活了。",
                        "category": "心理风险",
                        "level": "高",
                        "score": 0.92,
                        "keywords": ["不想活了"],
                        "rule_reason": "测试规则说明",
                        "llm_explanation": "测试解释",
                        "needs_attention": True,
                    },
                ],
            },
        }

    monkeypatch.setattr(public_data_service, "fetch_and_analyze", fake_fetch_and_analyze)

    response = client.post(
        "/api/public-sources/fetch",
        json={"source_id": "xidian-tieba", "limit": 2},
    )

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
                "category_distribution": {"正常文本": 1, "一般负面": 1},
                "level_distribution": {"正常": 1, "低": 1},
                "top_keywords": [{"keyword": "难受", "count": 1}],
                "wordcloud_keywords": [{"keyword": "课堂", "count": 2}],
                "attention_count": 0,
                "high_risk_texts": [],
            },
            "results": [
                {
                    "text": "今天备课顺利。",
                    "category": "正常文本",
                    "level": "正常",
                    "score": 0.08,
                    "keywords": [],
                    "rule_reason": "未命中明显风险规则。",
                    "llm_explanation": "当前文本整体为日常表达。",
                    "needs_attention": False,
                },
                {
                    "text": "最近有点难受。",
                    "category": "一般负面",
                    "level": "低",
                    "score": 0.43,
                    "keywords": ["难受"],
                    "rule_reason": "命中一般负面情绪词。",
                    "llm_explanation": "文本带有一定消极情绪。",
                    "needs_attention": False,
                },
            ],
        }

    monkeypatch.setattr(dataset_service, "get_default_dataset_analysis", fake_get_default_dataset_analysis)

    response = client.get("/api/datasets/default")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total"] == 2
    assert payload["summary"]["wordcloud_keywords"][0]["keyword"] == "课堂"
    assert payload["results"][0]["category"] == "正常文本"


def test_list_datasets(monkeypatch) -> None:
    monkeypatch.setattr(
        dataset_service,
        "list_datasets",
        lambda: [
            {
                "id": "educator-interviews-analysis",
                "name": "教师访谈分析结果",
                "description": "测试数据集",
                "file_name": "educator_interviews_analysis.csv",
                "data_kind": "analysis",
                "record_count": 669,
                "attention_count": 1,
                "updated_at": "2026-03-29 01:22",
                "is_default": True,
            }
        ],
    )

    response = client.get("/api/datasets")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["id"] == "educator-interviews-analysis"
    assert payload[0]["record_count"] == 669


def test_get_dataset_by_id(monkeypatch) -> None:
    def fake_get_dataset_analysis(dataset_id: str):
        assert dataset_id == "demo-texts"
        return {
            "summary": {
                "total": 1,
                "category_distribution": {"正常文本": 1},
                "level_distribution": {"正常": 1},
                "top_keywords": [],
                "wordcloud_keywords": [{"keyword": "课堂", "count": 1}],
                "attention_count": 0,
                "high_risk_texts": [],
            },
            "results": [
                {
                    "text": "今天课堂状态不错。",
                    "category": "正常文本",
                    "level": "正常",
                    "score": 0.06,
                    "keywords": [],
                    "rule_reason": "未命中明显风险规则。",
                    "llm_explanation": "文本整体表达较为日常平稳，当前未发现明显风险信号。",
                    "needs_attention": False,
                }
            ],
        }

    monkeypatch.setattr(dataset_service, "get_dataset_analysis", fake_get_dataset_analysis)

    response = client.get("/api/datasets/demo-texts")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total"] == 1
    assert payload["results"][0]["text"] == "今天课堂状态不错。"


def test_analysis_service_can_use_small_model_and_llm() -> None:
    class FakeSmallModel:
        def predict(self, text: str) -> SmallModelPrediction | None:
            return SmallModelPrediction(
                category="舆情风险",
                level="中",
                score=0.81,
                reason="小模型判断文本含有公开扩散倾向。",
            )

    class FakeLLM:
        def generate_explanation(self, **kwargs) -> str | None:
            return "这是来自大模型的解释。"

    class FakeFoundationModel:
        def predict(self, text: str):
            return None

        def generate_explanation(self, **kwargs) -> None:
            return None

    service = AnalysisService(
        small_model_engine=FakeSmallModel(),
        foundation_model_engine=FakeFoundationModel(),
        llm_engine=FakeLLM(),
    )

    result = service.analyze_text(
        payload=type("Payload", (), {"text": "这个学校处理投诉太离谱了，我准备曝光。"})()
    )

    assert result.category == "舆情风险"
    assert result.level in {"中", "高"}
    assert result.llm_explanation == "这是来自大模型的解释。"


def test_analysis_service_can_use_foundation_model() -> None:
    class FakeFoundationModel:
        def predict(self, text: str):
            return type(
                "Prediction",
                (),
                {
                    "category": "一般负面",
                    "level": "低",
                    "score": 0.61,
                    "reason": "更强模型判断文本主要体现压力和负面情绪。",
                },
            )()

        def generate_explanation(self, **kwargs) -> str:
            return "该文本主要体现出较明显的压力和负面感受，建议结合后续表述持续关注。"

    service = AnalysisService(foundation_model_engine=FakeFoundationModel())

    result = service.analyze_text(
        payload=type("Payload", (), {"text": "这段时间工作压力很大，我有点难受。"})()
    )

    assert result.category == "一般负面"
    assert result.level == "低"
    assert "大模型参考" in result.rule_reason
