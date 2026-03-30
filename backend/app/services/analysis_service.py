from __future__ import annotations

from collections import Counter

from app.engines.foundation_model.engine import FoundationModelEngine
from app.engines.llm.engine import LLMEngine
from app.engines.small_model.engine import SmallModelEngine
from app.schemas.analysis import (
    AnalysisRequest,
    AnalysisResult,
    BatchAnalysisRequest,
    BatchAnalysisResponse,
    BatchAnalysisSummary,
    DimensionScore,
    ExplanationRequest,
    IndicatorScore,
    KeywordCount,
)
from app.services.reference_library_service import ReferenceLibraryService
from app.services.scoring_service import ScoringService
from app.utils.text_segmentation import split_text_for_analysis
from app.utils.text_stats import extract_wordcloud_keywords


LONG_TEXT_CHAR_THRESHOLD = 320
LONG_TEXT_SEGMENT_THRESHOLD = 3


class AnalysisService:
    def __init__(
        self,
        small_model_engine: SmallModelEngine | None = None,
        foundation_model_engine: FoundationModelEngine | None = None,
        llm_engine: LLMEngine | None = None,
        scoring_service: ScoringService | None = None,
        reference_library_service: ReferenceLibraryService | None = None,
    ) -> None:
        self.small_model_engine = small_model_engine or SmallModelEngine()
        self.foundation_model_engine = foundation_model_engine or FoundationModelEngine()
        self.llm_engine = llm_engine or LLMEngine()
        self.scoring_service = scoring_service or ScoringService()
        self.reference_library_service = reference_library_service or ReferenceLibraryService()

    def analyze_text(self, payload: AnalysisRequest) -> AnalysisResult:
        return self._analyze_from_text(payload.text, use_llm=True)

    def analyze_batch(self, payload: BatchAnalysisRequest) -> BatchAnalysisResponse:
        results = [self._analyze_from_text(text, use_llm=False) for text in payload.texts]
        self._enrich_batch_explanations(results)
        return BatchAnalysisResponse(summary=self._build_summary(results), results=results)

    def generate_explanation(self, payload: ExplanationRequest) -> str:
        text = payload.text.strip()
        fallback = self._build_contextual_fallback(
            text=text,
            category=payload.category,
            level=payload.level,
            keywords=payload.keywords,
            rule_reason=payload.rule_reason,
            base_fallback=payload.fallback.strip() or None,
            dimension_scores=[],
            indicator_scores=[],
        )
        return self._generate_explanation(
            text=text,
            category=payload.category,
            level=payload.level,
            keywords=payload.keywords,
            rule_reason=payload.rule_reason,
            fallback=fallback,
        )

    def _analyze_from_text(self, raw_text: str, *, use_llm: bool) -> AnalysisResult:
        text = raw_text.strip()
        reference_library = self.reference_library_service.get_reference_library()
        score_result = self.scoring_service.score_text(
            text=text,
            reference_dimensions=reference_library.dimensions,
        )
        is_long_text = (
            len(text) >= LONG_TEXT_CHAR_THRESHOLD
            or score_result.segment_count >= LONG_TEXT_SEGMENT_THRESHOLD
        )

        fallback_explanation = self._build_contextual_fallback(
            text=text,
            category=score_result.category,
            level=score_result.level,
            keywords=score_result.matched_keywords,
            rule_reason=score_result.rule_reason,
            base_fallback="",
            is_long_text=is_long_text,
            dimension_scores=score_result.dimension_scores,
            indicator_scores=score_result.indicator_scores,
        )

        explanation = fallback_explanation
        if use_llm:
            explanation = self._generate_explanation(
                text=text,
                category=score_result.category,
                level=score_result.level,
                keywords=score_result.matched_keywords,
                rule_reason=score_result.rule_reason,
                fallback=fallback_explanation,
            )

        segment_previews = self._build_segment_previews(
            text=text,
            reference_library=reference_library,
            enabled=is_long_text,
        )

        return AnalysisResult(
            text=text,
            text_length=len(text),
            category=score_result.category,
            level=score_result.level,
            score=score_result.score,
            keywords=score_result.matched_keywords,
            rule_reason=score_result.rule_reason,
            llm_explanation=explanation,
            needs_attention=score_result.level in {"初显现", "中显现", "高显现"},
            score_breakdown=score_result.breakdown,
            dominant_dimension_id=score_result.dominant_dimension_id,
            dimension_scores=score_result.dimension_scores,
            indicator_scores=score_result.indicator_scores,
            reference_quotes=score_result.reference_quotes,
            is_long_text=is_long_text,
            segment_count=score_result.segment_count,
            segment_previews=segment_previews,
        )

    def _enrich_batch_explanations(self, results: list[AnalysisResult]) -> None:
        showcase_results = [result for result in results if result.needs_attention][:1]
        for result in showcase_results:
            result.llm_explanation = self._generate_explanation(
                text=result.text,
                category=result.category,
                level=result.level,
                keywords=result.keywords,
                rule_reason=result.rule_reason,
                fallback=result.llm_explanation,
            )

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
            candidate = (
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
            if self._looks_like_prompt_leak(candidate):
                return fallback
            return candidate
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
        is_long_text: bool = False,
        dimension_scores: list[DimensionScore] | None = None,
        indicator_scores: list[IndicatorScore] | None = None,
    ) -> str:
        snippet = self._trim_text(text)
        keyword_text = f"命中的线索包括“{'、'.join(keywords[:4])}”" if keywords else ""
        dimension_text = self._format_dimension_summary(dimension_scores or [])
        indicator_text = self._format_indicator_summary(indicator_scores or [], limit=3)
        metric_text = self._format_metric_summary(indicator_scores or [])
        detail_parts = [part for part in (dimension_text, indicator_text, metric_text) if part]
        detail_text = "；".join(detail_parts)

        if is_long_text:
            pieces = [
                "这是一段较长文本，系统已先按叙事片段拆分后再汇总分析。",
                f"整体上它在“{category}”层面最突出，当前为{level}。",
            ]
            if detail_text:
                pieces.append(detail_text + "。")
            elif keyword_text:
                pieces.append(keyword_text + "。")
            return "".join(pieces)

        if keyword_text:
            pieces = [
                f"这段输入在论文对应的“{category}”层面上最突出，当前为{level}。",
                keyword_text + "。",
            ]
            if detail_text:
                pieces.append(f"进一步看，{detail_text}。")
            return "".join(pieces)

        if snippet:
            pieces = [f"这段输入目前被归入“{category}”层面，当前为{level}。"]
            if detail_text:
                pieces.append(f"从已有证据看，{detail_text}。")
            else:
                pieces.append(
                    "它与论文中的教育家人格结构已有初步呼应，但还可以补充更具体的教学情境或价值判断。"
                )
            return "".join(pieces)

        return base_fallback or rule_reason

    def _format_dimension_summary(self, dimension_scores: list[DimensionScore]) -> str:
        if not dimension_scores:
            return ""

        top_dimensions = sorted(dimension_scores, key=lambda item: item.score, reverse=True)[:3]
        return "三重人格得分分别为" + "、".join(
            f"{item.name}{round(item.score * 100)}%" for item in top_dimensions
        )

    def _format_indicator_summary(
        self,
        indicator_scores: list[IndicatorScore],
        *,
        limit: int,
    ) -> str:
        if not indicator_scores:
            return ""

        top_indicators = sorted(indicator_scores, key=lambda item: item.score, reverse=True)[:limit]
        return "最突出的品质/行为是" + "、".join(
            f"{item.name}{round(item.score * 100)}%" for item in top_indicators
        )

    def _format_metric_summary(self, indicator_scores: list[IndicatorScore]) -> str:
        if not indicator_scores:
            return ""

        top_indicator = max(indicator_scores, key=lambda item: item.score, default=None)
        if top_indicator is None:
            return ""

        metric_map = {metric.id: metric for metric in top_indicator.metric_results}
        ordered_ids = (
            "keyword_hits",
            "cue_diversity",
            "segment_coverage",
            "density_per_1000_chars",
        )
        parts = []
        for metric_id in ordered_ids:
            metric = metric_map.get(metric_id)
            if metric is None:
                continue
            value = int(metric.value) if float(metric.value).is_integer() else round(metric.value, 2)
            parts.append(f"{metric.name}{value}{metric.unit}")

        if not parts:
            return ""

        return f"其中“{top_indicator.name}”的量化参考为" + "、".join(parts)

    def _trim_text(self, text: str, limit: int = 20) -> str:
        cleaned = " ".join(text.split())
        if not cleaned:
            return ""
        if len(cleaned) <= limit:
            return cleaned
        return f"{cleaned[:limit]}..."

    def _looks_like_prompt_leak(self, text: str) -> bool:
        leak_signals = (
            "请使用系统",
            "命名规则",
            "请只输出",
            "输出最终",
            "system",
            "prompt",
        )
        return any(signal in text.lower() for signal in leak_signals)

    def _build_segment_previews(
        self,
        *,
        text: str,
        reference_library,
        enabled: bool,
    ):
        if not enabled:
            return []

        segments = split_text_for_analysis(text)
        previews = []
        for index, segment in enumerate(segments, start=1):
            score_result = self.scoring_service.score_text(
                text=segment,
                reference_dimensions=reference_library.dimensions,
            )
            previews.append(
                {
                    "index": index,
                    "excerpt": self._trim_text(segment, limit=90),
                    "category": score_result.category,
                    "level": score_result.level,
                    "score": score_result.score,
                    "keywords": score_result.matched_keywords[:5],
                }
            )

        previews.sort(key=lambda item: item["score"], reverse=True)
        return previews[:8]

    def _build_summary(self, results: list[AnalysisResult]) -> BatchAnalysisSummary:
        category_counter = Counter(result.category for result in results)
        level_counter = Counter(result.level for result in results)
        keyword_counter = Counter(keyword for result in results for keyword in result.keywords)

        top_keywords = [
            KeywordCount(keyword=keyword, count=count)
            for keyword, count in keyword_counter.most_common(10)
        ]

        avg_score = round(sum(result.score for result in results) / len(results), 2) if results else 0.0
        return BatchAnalysisSummary(
            total=len(results),
            category_distribution=dict(category_counter),
            level_distribution=dict(level_counter),
            top_keywords=top_keywords,
            wordcloud_keywords=extract_wordcloud_keywords([result.text for result in results]),
            attention_count=sum(1 for result in results if result.needs_attention),
            high_risk_texts=[result for result in results if result.needs_attention][:10],
            avg_score=avg_score,
        )
