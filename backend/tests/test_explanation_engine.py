from app.engines.llm.engine import LLMEngine
from app.services.analysis_service import AnalysisService


def test_llm_engine_filters_prompt_leak_and_keeps_valid_sentence() -> None:
  engine = LLMEngine()

  result = engine._sanitize_output(
      raw_text="# 请只输出最终一句解释。\n这段输入在论文对应的职业人格层面上最突出，说明文本呈现出明显的课堂组织与学生回应能力。",
      fallback="这段输入与论文中的职业人格层面存在初步呼应。",
      category="职业人格",
      keywords=["学生"],
  )

  assert result == "这段输入在论文对应的职业人格层面上最突出，说明文本呈现出明显的课堂组织与学生回应能力。"


def test_analysis_service_prefers_foundation_model_for_explanation() -> None:
  class FakeFoundationModel:
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
          return "该文本与论文中的职业人格高度贴近，尤其强调了课堂反馈与任务落实。"

  class FakeLLM:
      def generate_explanation(self, **kwargs) -> str:
          return "这是本地解释层返回的结果。"

  service = AnalysisService(
      foundation_model_engine=FakeFoundationModel(),
      llm_engine=FakeLLM(),
  )

  result = service.analyze_text(
      payload=type("Payload", (), {"text": "我会把课堂反馈和项目任务一起设计进教学过程。"})()
  )

  assert result.llm_explanation == "该文本与论文中的职业人格高度贴近，尤其强调了课堂反馈与任务落实。"


def test_analysis_service_generates_contextual_fallback_explanation() -> None:
  service = AnalysisService()

  explanation = service.generate_explanation(
      payload=type(
          "Payload",
          (),
          {
              "text": "我想在课堂上给学生更多讨论和反馈的空间。",
              "category": "职业人格",
              "level": "中显现",
              "keywords": ["课堂", "学生", "反馈"],
              "rule_reason": "文本最集中地体现了“职业人格”。",
              "fallback": "",
          },
      )()
  )

  assert "职业人格" in explanation


def test_dynamic_scoring_varies_for_same_dimension_texts() -> None:
  class FakeFoundationModel:
      def generate_explanation(self, **kwargs):
          return None

  service = AnalysisService(foundation_model_engine=FakeFoundationModel())

  mild = service.analyze_text(
      payload=type("Payload", (), {"text": "我想多理解学生。"})()
  )
  strong = service.analyze_text(
      payload=type(
          "Payload",
          (),
          {"text": "我希望在课堂上先倾听学生、理解学生，再通过持续反馈陪伴他们成长。"},
      )()
  )

  assert mild.category == "职业人格"
  assert strong.category == "职业人格"
  assert strong.score > mild.score
  assert len(strong.score_breakdown) >= 2
