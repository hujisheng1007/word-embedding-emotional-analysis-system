from collections import Counter

from app.engines.foundation_model.engine import FoundationModelEngine, FoundationModelPrediction
from app.engines.llm.engine import LLMEngine
from app.engines.rules.engine import RuleDefinition, get_default_result, get_rule_definitions
from app.engines.small_model.engine import SmallModelEngine, SmallModelPrediction
from app.schemas.analysis import (
    AnalysisRequest,
    AnalysisResult,
    BatchAnalysisRequest,
    BatchAnalysisResponse,
    BatchAnalysisSummary,
    ExplanationRequest,
    KeywordCount,
)
from app.services.scoring_service import ScoringService
from app.utils.text_stats import extract_wordcloud_keywords


class AnalysisService:
    def __init__(
        self,
        small_model_engine: SmallModelEngine | None = None,
        foundation_model_engine: FoundationModelEngine | None = None,
        llm_engine: LLMEngine | None = None,
        scoring_service: ScoringService | None = None,
    ) -> None:
        self.small_model_engine = small_model_engine or SmallModelEngine()
        self.foundation_model_engine = foundation_model_engine or FoundationModelEngine()
        self.llm_engine = llm_engine or LLMEngine()
        self.scoring_service = scoring_service or ScoringService()

    def analyze_text(self, payload: AnalysisRequest) -> AnalysisResult:
        return self._analyze_from_text(payload.text, use_llm=True, use_foundation_model=True)

    def analyze_batch(self, payload: BatchAnalysisRequest) -> BatchAnalysisResponse:
        results = [
            self._analyze_from_text(text, use_llm=False, use_foundation_model=False)
            for text in payload.texts
        ]
        self._enrich_batch_explanations(results)
        summary = self._build_summary(results)
        return BatchAnalysisResponse(summary=summary, results=results)

    def generate_explanation(self, payload: ExplanationRequest) -> str:
        text = payload.text.strip()
        fallback = self._build_contextual_fallback(
            text=text,
            category=payload.category,
            level=payload.level,
            keywords=payload.keywords,
            rule_reason=payload.rule_reason,
            base_fallback=payload.fallback.strip() or None,
        )
        return self._generate_explanation(
            text=text,
            category=payload.category,
            level=payload.level,
            keywords=payload.keywords,
            rule_reason=payload.rule_reason,
            fallback=fallback,
        )

    def _analyze_from_text(
        self,
        raw_text: str,
        *,
        use_llm: bool,
        use_foundation_model: bool,
    ) -> AnalysisResult:
        text = raw_text.strip()
        matched_rule = self._match_rule(text)
        matched_keywords = self._collect_matched_keywords(text, matched_rule)
        fused = self._fuse_rule_and_model(text=text, rule=matched_rule, keywords=matched_keywords)

        if use_foundation_model:
            foundation_prediction = self._safe_foundation_model_predict(text)
            fused = self._apply_foundation_model_prediction(
                fused=fused,
                prediction=foundation_prediction,
            )

        score_result = self.scoring_service.score_text(
            text=text,
            category=str(fused["category"]),
            keywords=list(fused["keywords"]),
            model_score=float(fused["model_score"]) if fused["model_score"] is not None else None,
        )
        fused["score"] = score_result.score
        fused["level"] = score_result.level
        fused["score_breakdown"] = score_result.breakdown

        fallback_explanation = self._build_contextual_fallback(
            text=text,
            category=str(fused["category"]),
            level=str(fused["level"]),
            keywords=list(fused["keywords"]),
            rule_reason=str(fused["rule_reason"]),
            base_fallback=str(fused["llm_explanation"]),
        )

        explanation = fallback_explanation
        if use_llm:
            explanation = self._generate_explanation(
                text=text,
                category=str(fused["category"]),
                level=str(fused["level"]),
                keywords=list(fused["keywords"]),
                rule_reason=str(fused["rule_reason"]),
                fallback=fallback_explanation,
            )

        level = str(fused["level"])
        return AnalysisResult(
            text=text,
            category=str(fused["category"]),
            level=level,
            score=float(fused["score"]),
            keywords=list(fused["keywords"]),
            rule_reason=str(fused["rule_reason"]),
            llm_explanation=explanation,
            needs_attention=level in {"中", "高"},
            score_breakdown=list(fused["score_breakdown"]),
        )

    def _enrich_batch_explanations(self, results: list[AnalysisResult]) -> None:
        attention_results = [result for result in results if result.needs_attention][:1]
        for result in attention_results:
            result.llm_explanation = self._generate_explanation(
                text=result.text,
                category=result.category,
                level=result.level,
                keywords=result.keywords,
                rule_reason=result.rule_reason,
                fallback=result.llm_explanation,
            )

    def _match_rule(self, text: str) -> RuleDefinition:
        for rule in get_rule_definitions():
            if self._rule_matches(text, rule):
                return rule
        return get_default_result()

    def _rule_matches(self, text: str, rule: RuleDefinition) -> bool:
        if rule.trigger_groups:
            return all(any(keyword in text for keyword in group) for group in rule.trigger_groups)
        return any(keyword in text for keyword in rule.keywords)

    def _collect_matched_keywords(self, text: str, rule: RuleDefinition) -> list[str]:
        return [keyword for keyword in rule.keywords if keyword in text]

    def _fuse_rule_and_model(
        self,
        *,
        text: str,
        rule: RuleDefinition,
        keywords: list[str],
    ) -> dict[str, object]:
        model_result = self._safe_small_model_predict(text)
        if model_result is None:
            return {
                "category": rule.category,
                "level": rule.level,
                "score": rule.score,
                "keywords": keywords,
                "rule_reason": rule.rule_reason,
                "llm_explanation": rule.llm_explanation,
                "model_score": None,
                "score_breakdown": [],
            }

        if rule.level == "高":
            return {
                "category": rule.category,
                "level": rule.level,
                "score": max(rule.score, model_result.score),
                "keywords": keywords,
                "rule_reason": f"{rule.rule_reason} 小模型参考：{model_result.reason}",
                "llm_explanation": rule.llm_explanation,
                "model_score": model_result.score,
                "score_breakdown": [],
            }

        fused_category = model_result.category if rule.category == "正常文本" else rule.category
        fused_level = self._pick_higher_level(rule.level, model_result.level)

        return {
            "category": fused_category,
            "level": fused_level,
            "score": max(rule.score, model_result.score),
            "keywords": keywords,
            "rule_reason": f"{rule.rule_reason} 小模型参考：{model_result.reason}",
            "llm_explanation": rule.llm_explanation,
            "model_score": model_result.score,
            "score_breakdown": [],
        }

    def _safe_small_model_predict(self, text: str) -> SmallModelPrediction | None:
        try:
            return self.small_model_engine.predict(text)
        except Exception:
            return None

    def _safe_foundation_model_predict(self, text: str) -> FoundationModelPrediction | None:
        try:
            return self.foundation_model_engine.predict(text)
        except Exception:
            return None

    def _apply_foundation_model_prediction(
        self,
        *,
        fused: dict[str, object],
        prediction: FoundationModelPrediction | None,
    ) -> dict[str, object]:
        if prediction is None:
            return fused

        category = str(fused["category"])
        level = str(fused["level"])
        score = float(fused["score"])
        rule_reason = str(fused["rule_reason"])

        # 明确的心理高危硬触发仍保留最高优先级，避免被模型误降级。
        if category == "心理风险" and level == "高":
            fused["score"] = max(score, prediction.score)
            fused["rule_reason"] = f"{rule_reason} 大模型参考：{prediction.reason}"
            fused["model_score"] = prediction.score
            return fused

        # 其他情况默认由当前选中的大模型给出主判断，规则层作为可解释辅助。
        fused["category"] = prediction.category
        fused["level"] = prediction.level
        fused["score"] = max(score, prediction.score)
        fused["rule_reason"] = f"{rule_reason} 大模型参考：{prediction.reason}"
        fused["model_score"] = prediction.score
        return fused

    def _generate_explanation(
        self,
        *,
        text: str,
        category: str,
        level: str,
        keywords: list[str],
        rule_reason: str,
        fallback: str,
    ) -> str:
        foundation_explanation = self._safe_foundation_model_explanation(
            text=text,
            category=category,
            level=level,
            keywords=keywords,
            rule_reason=rule_reason,
            fallback=fallback,
        )
        if foundation_explanation:
            return foundation_explanation

        try:
            return (
                self.llm_engine.generate_explanation(
                    text=text,
                    category=category,
                    level=level,
                    keywords=keywords,
                    rule_reason=rule_reason,
                    fallback=fallback,
                )
                or fallback
            )
        except Exception:
            return fallback

    def _safe_foundation_model_explanation(
        self,
        *,
        text: str,
        category: str,
        level: str,
        keywords: list[str],
        rule_reason: str,
        fallback: str,
    ) -> str | None:
        try:
            return self.foundation_model_engine.generate_explanation(
                text=text,
                category=category,
                level=level,
                keywords=keywords,
                rule_reason=rule_reason,
                fallback=fallback,
            )
        except Exception:
            return None

    def _build_contextual_fallback(
        self,
        *,
        text: str,
        category: str,
        level: str,
        keywords: list[str],
        rule_reason: str,
        base_fallback: str | None = None,
    ) -> str:
        snippet = self._trim_text(text)
        keyword_text = f"重点词包括“{'、'.join(keywords[:3])}”" if keywords else ""

        if category == "心理风险":
            return (
                f"这段内容出现了明显的极端消极或自伤倾向表达，当前判定为{level}风险，"
                f"建议结合原文尽快人工复核。"
            )
        if category == "舆情风险":
            return (
                f"这段内容提到了校园相关对象，并伴随投诉、曝光或扩散倾向，当前判定为{level}舆情风险，"
                f"建议结合上下文持续关注。"
            )
        if category == "一般负面":
            if keyword_text:
                return f"这段内容带有较明显的负面情绪，{keyword_text}，目前更接近一般负面表达。"
            return "这段内容主要表达了压力、疲惫或不适感，当前更接近一般负面情绪表达。"
        if snippet:
            return f"这段内容更像日常求助或信息询问，暂未发现与“{snippet}”相关的明显风险信号。"
        return base_fallback or rule_reason

    def _trim_text(self, text: str, limit: int = 16) -> str:
        cleaned = " ".join(text.split())
        if not cleaned:
            return ""
        if len(cleaned) <= limit:
            return cleaned
        return f"{cleaned[:limit]}..."

    def _pick_higher_level(self, left: str, right: str) -> str:
        order = {"正常": 0, "低": 1, "中": 2, "高": 3}
        return left if order.get(left, 0) >= order.get(right, 0) else right

    def _build_summary(self, results: list[AnalysisResult]) -> BatchAnalysisSummary:
        category_counter = Counter(result.category for result in results)
        level_counter = Counter(result.level for result in results)
        keyword_counter = Counter(keyword for result in results for keyword in result.keywords)

        top_keywords = [
            KeywordCount(keyword=keyword, count=count)
            for keyword, count in keyword_counter.most_common(10)
        ]

        return BatchAnalysisSummary(
            total=len(results),
            category_distribution=dict(category_counter),
            level_distribution=dict(level_counter),
            top_keywords=top_keywords,
            wordcloud_keywords=extract_wordcloud_keywords([result.text for result in results]),
            attention_count=sum(1 for result in results if result.needs_attention),
            high_risk_texts=[result for result in results if result.needs_attention][:10],
        )
