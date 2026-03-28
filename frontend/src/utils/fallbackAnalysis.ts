import type {
  AnalysisResult,
  BatchAnalysisResponse,
  BatchAnalysisSummary,
  KeywordCount
} from "../types/analysis";

interface RuleDefinition {
  category: string;
  level: string;
  score: number;
  keywords: string[];
  rule_reason: string;
  llm_explanation: string;
}

const rules: RuleDefinition[] = [
  {
    category: "心理风险",
    level: "高",
    score: 0.92,
    keywords: ["崩溃", "不想继续", "活不下去", "不想活了", "结束自己"],
    rule_reason: "命中心理高风险关键词，规则层判定为优先关注对象。",
    llm_explanation: "文本包含明显极端消极和绝望表达，建议优先人工复核。"
  },
  {
    category: "舆情风险",
    level: "中",
    score: 0.76,
    keywords: ["投诉", "学校", "曝光", "离谱", "维权", "垃圾"],
    rule_reason: "命中校园舆情相关词，并伴随负面或扩散倾向表达。",
    llm_explanation: "文本含有较强负面评价或公开扩散倾向，存在舆情传播风险。"
  },
  {
    category: "一般负面",
    level: "低",
    score: 0.43,
    keywords: ["烦", "累", "倒霉", "难受", "无语", "不开心"],
    rule_reason: "命中一般负面情绪词，但未达到高风险触发条件。",
    llm_explanation: "文本带有一定消极情绪，建议结合上下文继续观察。"
  }
];

const defaultResult: RuleDefinition = {
  category: "正常文本",
  level: "正常",
  score: 0.08,
  keywords: [],
  rule_reason: "未命中明显风险规则。",
  llm_explanation: "当前文本整体为正常表达。"
};

export function analyzeTextFallback(text: string): AnalysisResult {
  const normalizedText = text.trim();
  const matchedRule =
    rules.find((rule) => rule.keywords.some((keyword) => normalizedText.includes(keyword))) ??
    defaultResult;
  const keywords = matchedRule.keywords.filter((keyword) => normalizedText.includes(keyword));

  return {
    text: normalizedText,
    category: matchedRule.category,
    level: matchedRule.level,
    score: matchedRule.score,
    keywords,
    rule_reason: matchedRule.rule_reason,
    llm_explanation: matchedRule.llm_explanation,
    needs_attention: matchedRule.level === "中" || matchedRule.level === "高"
  };
}

function buildSummary(results: AnalysisResult[]): BatchAnalysisSummary {
  const categoryDistribution: Record<string, number> = {};
  const levelDistribution: Record<string, number> = {};
  const keywordDistribution: Record<string, number> = {};

  results.forEach((result) => {
    categoryDistribution[result.category] = (categoryDistribution[result.category] ?? 0) + 1;
    levelDistribution[result.level] = (levelDistribution[result.level] ?? 0) + 1;
    result.keywords.forEach((keyword) => {
      keywordDistribution[keyword] = (keywordDistribution[keyword] ?? 0) + 1;
    });
  });

  const topKeywords: KeywordCount[] = Object.entries(keywordDistribution)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([keyword, count]) => ({ keyword, count }));

  return {
    total: results.length,
    category_distribution: categoryDistribution,
    level_distribution: levelDistribution,
    top_keywords: topKeywords,
    attention_count: results.filter((result) => result.needs_attention).length,
    high_risk_texts: results.filter((result) => result.needs_attention).slice(0, 10)
  };
}

export function analyzeBatchFallback(texts: string[]): BatchAnalysisResponse {
  const results = texts.map((text) => analyzeTextFallback(text));
  return {
    summary: buildSummary(results),
    results
  };
}
