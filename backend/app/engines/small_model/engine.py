from dataclasses import dataclass

import httpx

from app.core.settings import get_settings


@dataclass(frozen=True)
class SmallModelPrediction:
    category: str
    level: str
    score: float
    reason: str


class SmallModelEngine:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def enabled(self) -> bool:
        return self.settings.small_model_enabled

    def predict(self, text: str) -> SmallModelPrediction | None:
        if not self.enabled:
            return None

        payload = {
            "text": text,
            "labels": ["心理风险", "舆情风险", "一般负面", "正常文本"],
        }
        response = httpx.post(
            self.settings.small_model_endpoint,
            json=payload,
            timeout=self.settings.small_model_timeout,
        )
        response.raise_for_status()
        result = response.json()

        return SmallModelPrediction(
            category=result["category"],
            level=result["level"],
            score=float(result["score"]),
            reason=result.get("reason", "来自小模型预测结果。"),
        )
