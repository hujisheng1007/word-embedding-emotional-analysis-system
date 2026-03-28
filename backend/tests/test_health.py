from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_single_analysis() -> None:
    response = client.post(
        "/api/analyze",
        json={"text": "最近真的要崩溃了，不想继续了", "mode": "hybrid"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["category"] == "心理风险"
    assert payload["level"] == "高"
    assert payload["needs_attention"] is True
    assert "崩溃" in payload["keywords"]


def test_batch_analysis() -> None:
    response = client.post(
        "/api/analyze/batch",
        json={
            "texts": [
                "最近真的要崩溃了，不想继续了",
                "这个学校处理问题太离谱了，我要发到网上曝光",
                "今天天气不错，课也很顺利",
            ],
            "mode": "hybrid",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total"] == 3
    assert payload["summary"]["attention_count"] == 2
    assert payload["summary"]["category_distribution"]["心理风险"] == 1
    assert len(payload["results"]) == 3

