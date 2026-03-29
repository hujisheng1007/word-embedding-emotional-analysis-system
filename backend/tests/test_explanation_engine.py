from app.engines.llm.engine import LLMEngine
from app.services.analysis_service import AnalysisService


def test_llm_engine_filters_prompt_leak_and_keeps_valid_sentence() -> None:
    engine = LLMEngine()

    result = engine._sanitize_output(
        raw_text="# 请只输出最终一句解释。\n文本表现出明显的压力和负面情绪，建议持续关注后续表述。",
        fallback="文本表现出一定负面情绪，但暂未达到高风险触发条件。",
        category="一般负面",
        keywords=["压力"],
    )

    assert result == "文本表现出明显的压力和负面情绪，建议持续关注后续表述。"


def test_analysis_service_prefers_foundation_model_for_explanation() -> None:
    class FakeFoundationModel:
        def predict(self, text: str):
            return None

        def generate_explanation(
            self,
            *,
            text: str,
            category: str,
            level: str,
            keywords: list[str],
            rule_reason: str,
            fallback: str,
        ) -> str:
            return "该文本主要体现出较明显的负面情绪，建议结合后续表述持续关注。"

    class FakeLLM:
        def generate_explanation(self, **kwargs) -> str:
            return "这是本地解释层返回的结果。"

    service = AnalysisService(
        foundation_model_engine=FakeFoundationModel(),
        llm_engine=FakeLLM(),
    )

    result = service.analyze_text(
        payload=type("Payload", (), {"text": "太崩溃了，好想把学校炸了"})()
    )

    assert result.llm_explanation == "该文本主要体现出较明显的负面情绪，建议结合后续表述持续关注。"


def test_analysis_service_generates_contextual_fallback_explanation() -> None:
    service = AnalysisService()

    explanation = service.generate_explanation(
        payload=type(
            "Payload",
            (),
            {
                "text": "求助一下学长学姐，西安军械修理厂怎么样。",
                "category": "正常文本",
                "level": "正常",
                "keywords": [],
                "rule_reason": "未命中明显风险规则。",
                "fallback": "",
            },
        )()
    )

    assert "日常求助" in explanation or "西安军械修理厂" in explanation


def test_dynamic_scoring_varies_for_same_category_texts() -> None:
    class FakeFoundationModel:
        def predict(self, text: str):
            return None

        def generate_explanation(self, **kwargs):
            return None

    service = AnalysisService(foundation_model_engine=FakeFoundationModel())

    mild = service.analyze_text(
        payload=type("Payload", (), {"text": "最近很累，作业有点多。"})()
    )
    strong = service.analyze_text(
        payload=type("Payload", (), {"text": "最近真的快崩溃了，压力特别大，一直都很难受。"})()
    )

    assert mild.category == "一般负面"
    assert strong.category == "一般负面"
    assert strong.score > mild.score
    assert len(strong.score_breakdown) >= 2
