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
  triggerGroups?: string[][];
  ruleReason: string;
  llmExplanation: string;
}

const rules: RuleDefinition[] = [
  {
    category: "心理风险",
    level: "高",
    score: 0.92,
    keywords: ["不想活了", "活不下去", "结束自己", "结束生命", "轻生", "自杀", "没有活着的意义"],
    ruleReason: "命中心理高风险强触发表达，规则层判定为优先关注对象。",
    llmExplanation: "文本包含明显的极端消极或自伤倾向表达，建议优先人工复核。"
  },
  {
    category: "舆情风险",
    level: "中",
    score: 0.76,
    keywords: ["学校", "学院", "宿舍", "食堂", "老师", "辅导员", "课程", "招生", "管理", "投诉", "曝光", "维权", "举报", "发帖", "热搜", "扩散", "离谱", "垃圾", "推诿", "不作为"],
    triggerGroups: [
      ["学校", "学院", "宿舍", "食堂", "老师", "辅导员", "课程", "招生", "管理", "校园"],
      ["投诉", "曝光", "维权", "举报", "发帖", "热搜", "扩散", "离谱", "垃圾", "推诿", "不作为"]
    ],
    ruleReason: "文本同时出现校园对象和负面扩散倾向表达，存在舆情传播风险。",
    llmExplanation: "文本对校园相关对象表达了较强负面评价，并伴随扩散或对抗倾向，建议重点关注。"
  },
  {
    category: "一般负面",
    level: "低",
    score: 0.43,
    keywords: ["太累", "很累", "疲惫", "难受", "不开心", "压力", "焦虑", "无奈", "不知所措", "崩溃", "心烦", "委屈", "失落", "烦躁", "烦闷"],
    ruleReason: "命中一般负面情绪词，但未达到高风险触发条件。",
    llmExplanation: "文本体现出一定负面情绪，建议结合上下文继续观察。"
  }
];

const defaultResult: RuleDefinition = {
  category: "正常文本",
  level: "正常",
  score: 0.08,
  keywords: [],
  ruleReason: "未命中明显风险规则。",
  llmExplanation: "当前文本整体为日常表达。"
};

const stopwords = new Set([
  "我们",
  "你们",
  "他们",
  "她们",
  "自己",
  "一个",
  "这个",
  "那个",
  "不是",
  "然后",
  "因为",
  "所以",
  "就是",
  "还有",
  "如果",
  "的话",
  "时候",
  "觉得",
  "可能",
  "现在",
  "已经",
  "没有",
  "这样",
  "一些",
  "很多",
  "这种",
  "比较",
  "可以",
  "一种",
  "什么",
  "怎么",
  "这些",
  "应该",
  "比如",
  "感觉",
  "方面",
  "能够",
  "问题",
  "工作",
  "其实"
]);

const edgeStopChars = new Set("的了一是在和与及就都也很把让对给将被向从到地得着而并但或其我个这那".split(""));

function matchesRule(text: string, rule: RuleDefinition): boolean {
  if (rule.triggerGroups?.length) {
    return rule.triggerGroups.every((group) => group.some((keyword) => text.includes(keyword)));
  }

  return rule.keywords.some((keyword) => text.includes(keyword));
}

export function analyzeTextFallback(text: string): AnalysisResult {
  const normalizedText = text.trim();
  const matchedRule = rules.find((rule) => matchesRule(normalizedText, rule)) ?? defaultResult;
  const keywords = matchedRule.keywords.filter((keyword) => normalizedText.includes(keyword));

  return {
    text: normalizedText,
    category: matchedRule.category,
    level: matchedRule.level,
    score: matchedRule.score,
    keywords,
    rule_reason: matchedRule.ruleReason,
    llm_explanation: matchedRule.llmExplanation,
    needs_attention: matchedRule.level === "中" || matchedRule.level === "高"
  };
}

function extractWordcloudKeywords(texts: string[]): KeywordCount[] {
  const counts: Record<string, number> = {};

  texts.forEach((text) => {
    const seen = new Set<string>();
    const blocks = text.match(/[\u4e00-\u9fff]{2,}/g) ?? [];
    blocks.forEach((block) => {
      const maxN = Math.min(4, block.length);
      for (let size = 2; size <= maxN; size += 1) {
        for (let start = 0; start <= block.length - size; start += 1) {
          const token = block.slice(start, start + size);
          if (!isValidToken(token)) {
            continue;
          }
          seen.add(token);
        }
      }
    });
    seen.forEach((token) => {
      counts[token] = (counts[token] ?? 0) + 1;
    });
  });

  const selected: Array<[string, number]> = [];
  Object.entries(counts)
    .sort((left, right) => {
      if (right[1] !== left[1]) {
        return right[1] - left[1];
      }
      if (right[0].length !== left[0].length) {
        return right[0].length - left[0].length;
      }
      return left[0].localeCompare(right[0], "zh-CN");
    })
    .forEach(([token, count]) => {
      if (count < 2) {
        return;
      }
      if (selected.some(([chosen, chosenCount]) => chosen.includes(token) && chosenCount >= count)) {
        return;
      }
      if (selected.length < 40) {
        selected.push([token, count]);
      }
    });

  return selected.map(([keyword, count]) => ({ keyword, count }));
}

function isValidToken(token: string): boolean {
  if (token.length < 2 || stopwords.has(token)) {
    return false;
  }
  if (edgeStopChars.has(token[0]) || edgeStopChars.has(token[token.length - 1])) {
    return false;
  }
  return new Set(token).size > 1;
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
    wordcloud_keywords: extractWordcloudKeywords(results.map((result) => result.text)),
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
