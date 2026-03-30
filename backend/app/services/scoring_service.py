from __future__ import annotations

from dataclasses import dataclass

from app.schemas.analysis import (
    DimensionScore,
    IndicatorMetricResult,
    IndicatorScore,
    ReferenceDimension,
    ScoreFactor,
)
from app.services.educator_taxonomy import (
    EDUCATOR_GROUPS,
    EDUCATOR_INDICATORS,
    INDICATOR_METRIC_BENCHMARKS,
    get_group_definition_map,
)
from app.utils.text_segmentation import split_text_for_analysis


@dataclass(frozen=True)
class ScoreResult:
    score: float
    level: str
    category: str
    dominant_dimension_id: str
    dimension_scores: list[DimensionScore]
    indicator_scores: list[IndicatorScore]
    reference_quotes: list[str]
    matched_keywords: list[str]
    rule_reason: str
    breakdown: list[ScoreFactor]
    segment_count: int


class ScoringService:
    def score_text(
        self,
        *,
        text: str,
        reference_dimensions: list[ReferenceDimension],
    ) -> ScoreResult:
        normalized_text = " ".join(text.split())
        segments = split_text_for_analysis(text)
        segment_count = max(1, len(segments))

        indicator_scores = [
            self._score_indicator(normalized_text, segments, indicator)
            for indicator in EDUCATOR_INDICATORS
        ]
        indicator_scores.sort(key=lambda item: item.score, reverse=True)

        group_scores = self._build_group_scores(indicator_scores)
        group_scores.sort(key=lambda item: item.score, reverse=True)
        dominant_group = group_scores[0]

        breadth_count = sum(1 for item in group_scores if item.score >= 0.26)
        narrative_value = 0.16 if len(normalized_text) >= 1200 else 0.12 if len(normalized_text) >= 400 else 0.08 if len(normalized_text) >= 120 else 0.04
        breadth_value = min(0.14, max(0, breadth_count - 1) * 0.05)
        final_score = round(min(0.98, dominant_group.score * 0.82 + breadth_value + narrative_value), 2)

        top_indicators = [
            item for item in indicator_scores if item.group_id == dominant_group.id
        ][:4]
        matched_keywords = []
        for indicator in top_indicators:
            for keyword in indicator.matched_keywords:
                if keyword not in matched_keywords:
                    matched_keywords.append(keyword)

        breakdown: list[ScoreFactor] = []
        self._append_factor(
            breakdown,
            name="主人格显现度",
            value=round(dominant_group.score * 0.82, 2),
            description=f"当前文本最显著地体现了“{dominant_group.name}”这层人格。",
        )
        self._append_factor(
            breakdown,
            name="人格横向展开",
            value=round(breadth_value, 2),
            description="若文本同时触达多层人格，会提高整体画像的完整度。",
        )
        self._append_factor(
            breakdown,
            name="叙事长度增益",
            value=round(narrative_value, 2),
            description="较长的叙事或传记材料能提供更丰富的证据密度与跨段线索。",
        )

        return ScoreResult(
            score=final_score,
            level=self._level_from_score(final_score),
            category=dominant_group.name,
            dominant_dimension_id=dominant_group.id,
            dimension_scores=group_scores,
            indicator_scores=indicator_scores,
            reference_quotes=self._lookup_reference_quotes(reference_dimensions, dominant_group.id),
            matched_keywords=matched_keywords[:8],
            rule_reason=self._build_rule_reason(dominant_group.name, top_indicators, matched_keywords, segment_count),
            breakdown=breakdown,
            segment_count=segment_count,
        )

    def _score_indicator(self, text: str, segments: list[str], indicator) -> IndicatorScore:
        keyword_hits = 0
        segment_hit_count = 0
        matched_keywords: list[str] = []

        for segment in segments or [text]:
            current_segment_hit = False
            for keyword in indicator.cue_keywords:
                hits = segment.count(keyword)
                if hits <= 0:
                    continue
                keyword_hits += hits
                current_segment_hit = True
                if keyword not in matched_keywords:
                    matched_keywords.append(keyword)
            if current_segment_hit:
                segment_hit_count += 1

        total_segments = max(1, len(segments))
        cue_diversity = len(matched_keywords)
        segment_coverage_ratio = round(segment_hit_count / total_segments, 4)
        density_per_1000_chars = round(keyword_hits * 1000 / max(len(text), 1), 2)
        context_bonus = 0.08 if any(token in text for token in ("教育", "教师", "学生", "课堂", "成长", "社会")) else 0.0

        metric_results = [
            self._build_metric_result("keyword_hits", float(keyword_hits)),
            self._build_metric_result("cue_diversity", float(cue_diversity)),
            self._build_metric_result("segment_coverage", round(segment_coverage_ratio * 100, 2)),
            self._build_metric_result("density_per_1000_chars", density_per_1000_chars),
        ]

        keyword_hit_score = min(1.0, keyword_hits / self._metric_high("keyword_hits"))
        diversity_score = min(1.0, cue_diversity / self._metric_high("cue_diversity"))
        coverage_score = min(1.0, (segment_coverage_ratio * 100) / self._metric_high("segment_coverage"))
        density_score = min(1.0, density_per_1000_chars / self._metric_high("density_per_1000_chars"))

        score = round(
            min(
                0.96,
                keyword_hit_score * 0.34
                + diversity_score * 0.26
                + coverage_score * 0.22
                + density_score * 0.10
                + context_bonus,
            ),
            2,
        )

        group_name = get_group_definition_map()[indicator.group_id].name
        return IndicatorScore(
            id=indicator.id,
            name=indicator.name,
            group_id=indicator.group_id,
            group_name=group_name,
            aspect_type=indicator.aspect_type,
            score=score,
            evidence_count=keyword_hits,
            matched_keywords=matched_keywords[:8],
            description=indicator.description,
            metric_results=metric_results,
        )

    def _build_metric_result(self, benchmark_id: str, value: float) -> IndicatorMetricResult:
        benchmark = next(item for item in INDICATOR_METRIC_BENCHMARKS if item.id == benchmark_id)
        if value >= benchmark.high:
            band = "高"
        elif value >= benchmark.medium:
            band = "中"
        elif value >= benchmark.low:
            band = "低"
        else:
            band = "待补足"
        return IndicatorMetricResult(
            id=benchmark.id,
            name=benchmark.name,
            unit=benchmark.unit,
            value=round(value, 2),
            description=benchmark.description,
            low=benchmark.low,
            medium=benchmark.medium,
            high=benchmark.high,
            band=band,
        )

    def _metric_high(self, benchmark_id: str) -> float:
        benchmark = next(item for item in INDICATOR_METRIC_BENCHMARKS if item.id == benchmark_id)
        return benchmark.high

    def _build_group_scores(self, indicator_scores: list[IndicatorScore]) -> list[DimensionScore]:
        group_definition_map = get_group_definition_map()
        grouped_scores: list[DimensionScore] = []

        for group in EDUCATOR_GROUPS:
            current_items = [item for item in indicator_scores if item.group_id == group.id]
            if current_items:
                top_two = sorted(current_items, key=lambda item: item.score, reverse=True)[:2]
                avg_score = sum(item.score for item in current_items) / len(current_items)
                top_score = sum(item.score for item in top_two) / len(top_two)
                group_score = round(min(0.96, avg_score * 0.42 + top_score * 0.58), 2)
                matched_keywords: list[str] = []
                for item in current_items:
                    for keyword in item.matched_keywords:
                        if keyword not in matched_keywords:
                            matched_keywords.append(keyword)
                evidence_count = sum(item.evidence_count for item in current_items)
            else:
                group_score = 0.0
                matched_keywords = []
                evidence_count = 0

            grouped_scores.append(
                DimensionScore(
                    id=group.id,
                    name=group_definition_map[group.id].name,
                    score=group_score,
                    evidence_count=evidence_count,
                    matched_keywords=matched_keywords[:10],
                    description=group_definition_map[group.id].description,
                )
            )

        return grouped_scores

    def _lookup_reference_quotes(
        self,
        reference_dimensions: list[ReferenceDimension],
        dimension_id: str,
    ) -> list[str]:
        for dimension in reference_dimensions:
            if dimension.id == dimension_id:
                return [quote.text for quote in dimension.sample_quotes[:2]]
        return []

    def _build_rule_reason(
        self,
        group_name: str,
        top_indicators: list[IndicatorScore],
        matched_keywords: list[str],
        segment_count: int,
    ) -> str:
        active_indicators = [item.name for item in top_indicators if item.score > 0][:3]
        indicator_text = "、".join(active_indicators) if active_indicators else "相关品质/行为"
        if matched_keywords:
            joined_keywords = "、".join(matched_keywords[:5])
            return (
                f"文本最集中地体现了“{group_name}”，主要落在 {indicator_text}；"
                f"线索词包括 {joined_keywords}，共覆盖 {segment_count} 个分析分段。"
            )
        return f"文本当前更接近“{group_name}”，但显式证据仍偏少，建议补充更具体的情节与价值判断。"

    def _append_factor(
        self,
        breakdown: list[ScoreFactor],
        *,
        name: str,
        value: float,
        description: str,
    ) -> None:
        if abs(value) < 0.005:
            return
        breakdown.append(
            ScoreFactor(
                name=name,
                value=round(value, 2),
                description=description,
            )
        )

    def _level_from_score(self, score: float) -> str:
        if score >= 0.8:
            return "高显现"
        if score >= 0.58:
            return "中显现"
        if score >= 0.34:
            return "初显现"
        return "待补足"
