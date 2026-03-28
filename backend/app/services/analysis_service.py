from collections import Counter

from app.engines.rules.engine import (
    RuleDefinition,
    get_default_result,
    get_rule_definitions,
)
from app.schemas.analysis import (
    AnalysisRequest,
    AnalysisResult,
    BatchAnalysisRequest,
    BatchAnalysisResponse,
    BatchAnalysisSummary,
    KeywordCount,
)


class AnalysisService:
    def analyze_text(self, payload: AnalysisRequest) -> AnalysisResult:
        return self._analyze_from_text(payload.text)

    def analyze_batch(self, payload: BatchAnalysisRequest) -> BatchAnalysisResponse:
        results = [self._analyze_from_text(text) for text in payload.texts]
        summary = self._build_summary(results)
        return BatchAnalysisResponse(summary=summary, results=results)

    def _analyze_from_text(self, raw_text: str) -> AnalysisResult:
        text = raw_text.strip()
        matched_rule = self._match_rule(text)
        matched_keywords = [keyword for keyword in matched_rule.keywords if keyword in text]

        return AnalysisResult(
            text=text,
            category=matched_rule.category,
            level=matched_rule.level,
            score=matched_rule.score,
            keywords=matched_keywords,
            rule_reason=matched_rule.rule_reason,
            llm_explanation=matched_rule.llm_explanation,
            needs_attention=matched_rule.level in {"中", "高"},
        )

    def _match_rule(self, text: str) -> RuleDefinition:
        for rule in get_rule_definitions():
            if any(keyword in text for keyword in rule.keywords):
                return rule
        return get_default_result()

    def _build_summary(self, results: list[AnalysisResult]) -> BatchAnalysisSummary:
        category_counter = Counter(result.category for result in results)
        level_counter = Counter(result.level for result in results)
        keyword_counter = Counter(
            keyword
            for result in results
            for keyword in result.keywords
        )

        top_keywords = [
            KeywordCount(keyword=keyword, count=count)
            for keyword, count in keyword_counter.most_common(10)
        ]
        high_risk_texts = [
            result
            for result in results
            if result.level == "高" or result.needs_attention
        ]

        return BatchAnalysisSummary(
            total=len(results),
            category_distribution=dict(category_counter),
            level_distribution=dict(level_counter),
            top_keywords=top_keywords,
            attention_count=sum(1 for result in results if result.needs_attention),
            high_risk_texts=high_risk_texts[:10],
        )
