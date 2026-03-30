import type {
  AnalysisResult,
  BatchAnalysisResponse,
  BatchAnalysisSummary,
  DimensionScore,
  IndicatorMetricResult,
  IndicatorScore,
  KeywordCount,
  TextSegmentPreview
} from "../types/analysis";

interface IndicatorDefinition {
  id: string;
  name: string;
  groupId: string;
  groupName: string;
  aspectType: string;
  description: string;
  keywords: string[];
}

const indicators: IndicatorDefinition[] = [
  { id: "emotional_stability", name: "情绪稳定", groupId: "natural_personality", groupName: "自然人格", aspectType: "quality", description: "面对压力时保持平和、坚韧与稳定投入。", keywords: ["稳定", "情绪", "压力", "调节", "坚韧"] },
  { id: "intrinsic_motivation", name: "乐教热情", groupId: "natural_personality", groupName: "自然人格", aspectType: "quality", description: "对教育事业具有持续热爱和职业信念。", keywords: ["热爱", "热情", "信念", "初心", "理想"] },
  { id: "open_growth", name: "开放成长", groupId: "natural_personality", groupName: "自然人格", aspectType: "quality", description: "愿意学习、接纳变化并主动尝试新路径。", keywords: ["学习", "探索", "成长", "更新", "尝试"] },
  { id: "self_regulation_behavior", name: "自我调节行为", groupId: "natural_personality", groupName: "自然人格", aspectType: "behavior", description: "困难情境中主动调整节奏和状态。", keywords: ["调整", "调节", "修复", "坚持", "应对"] },
  { id: "active_learning_behavior", name: "主动学习行为", groupId: "natural_personality", groupName: "自然人格", aspectType: "behavior", description: "主动阅读、借鉴、进修并转化为实践更新。", keywords: ["阅读", "进修", "学习", "借鉴", "更新"] },
  { id: "teaching_wisdom", name: "教学机敏", groupId: "professional_personality", groupName: "职业人格", aspectType: "quality", description: "课堂组织、策略切换与因材施教能力。", keywords: ["课堂", "教学", "备课", "反馈", "策略", "设计"] },
  { id: "student_affinity", name: "师生亲和", groupId: "professional_personality", groupName: "职业人格", aspectType: "quality", description: "理解学生并形成温暖互动关系。", keywords: ["学生", "家长", "理解", "沟通", "陪伴", "关爱"] },
  { id: "professional_perseverance", name: "专业精进", groupId: "professional_personality", groupName: "职业人格", aspectType: "quality", description: "长期投入、反思改进并持续深耕专业。", keywords: ["反思", "精进", "专业", "积累", "长期", "改进"] },
  { id: "classroom_design_behavior", name: "课堂设计行为", groupId: "professional_personality", groupName: "职业人格", aspectType: "behavior", description: "把项目、活动和反馈落到课堂结构上。", keywords: ["设计", "项目", "活动", "任务", "反馈", "课堂"] },
  { id: "communication_coordination_behavior", name: "沟通协同行为", groupId: "professional_personality", groupName: "职业人格", aspectType: "behavior", description: "与学生、家长和同事形成教育协同。", keywords: ["沟通", "协调", "合作", "家长", "同事", "协同"] },
  { id: "self_transcendence", name: "使命超越", groupId: "moral_personality", groupName: "道德人格", aspectType: "quality", description: "超越小我，转向使命、意义与更高价值。", keywords: ["使命", "意义", "超越", "价值", "大我", "理想"] },
  { id: "altruistic_care", name: "利他关怀", groupId: "moral_personality", groupName: "道德人格", aspectType: "quality", description: "以学生为先、乐教爱生并甘于奉献。", keywords: ["奉献", "利他", "爱生", "关怀", "无私", "温度"] },
  { id: "collective_commitment", name: "社会担当", groupId: "moral_personality", groupName: "道德人格", aspectType: "quality", description: "将教育与国家、社会、文化责任联系起来。", keywords: ["国家", "社会", "文化", "担当", "责任", "文明"] },
  { id: "ethical_action_behavior", name: "道德践履行为", groupId: "moral_personality", groupName: "道德人格", aspectType: "behavior", description: "把价值判断转化为真实行动与长期承担。", keywords: ["践行", "示范", "选择", "行动", "影响", "坚持"] },
  { id: "cultural_guidance_behavior", name: "文化引领行为", groupId: "moral_personality", groupName: "道德人格", aspectType: "behavior", description: "把教育与文化传承和社会方向联系起来。", keywords: ["文化", "传承", "弘道", "引领", "方向", "社会"] }
];

const groupDescriptions: Record<string, string> = {
  natural_personality: "先行基础，关注稳定积极的情绪内核、成长取向和心理韧性。",
  professional_personality: "现实依托，关注教学智慧、师生互动、专业精进和职业行动力。",
  moral_personality: "根本支撑，关注使命感、利他精神、文化担当与社会价值取向。"
};

const referenceQuotes: Record<string, string[]> = {
  natural_personality: ["对教育的热爱和稳定的内在信念，是支撑我持续走下去的根本动力。"],
  professional_personality: ["如果教师愿意在课堂设计、沟通方式和反馈节奏上持续调整，很多问题会被化解。"],
  moral_personality: ["教育家真正重要的不是个人成就，而是能否把价值和方向感带给更多人。"]
};

const metricTemplates = {
  keyword_hits: { name: "关键词命中数", unit: "次", low: 1, medium: 3, high: 6, description: "直接相关线索词的命中次数。" },
  cue_diversity: { name: "线索多样度", unit: "项", low: 1, medium: 2, high: 4, description: "命中的不同线索词数量。" },
  segment_coverage: { name: "段落覆盖率", unit: "%", low: 15, medium: 35, high: 60, description: "命中线索的分段占比。" },
  density_per_1000_chars: { name: "千字证据密度", unit: "次/千字", low: 2, medium: 5, high: 9, description: "按文本长度归一化后的证据密度。" }
} as const;

const stopwords = new Set(["我们", "你们", "他们", "自己", "一个", "这个", "那个", "不是", "然后", "因为", "所以", "就是", "还有", "如果", "的话", "觉得", "已经", "这样", "一些", "很多", "比较", "可以", "什么", "怎么", "应该", "其实"]);
const edgeStopChars = new Set("的了一是在和与及就都也很把让对给将被向从到地得着而并但或其我个这那".split(""));
const longTextCharThreshold = 320;
const longTextSegmentThreshold = 3;

function scoreLevel(score: number): string {
  if (score >= 0.8) return "高显现";
  if (score >= 0.58) return "中显现";
  if (score >= 0.34) return "初显现";
  return "待补足";
}

function splitTextForAnalysis(text: string): string[] {
  const paragraphs = text
    .replace(/\r/g, "\n")
    .split(/\n+/)
    .map((item) => item.trim())
    .filter(Boolean);
  const base = paragraphs.length > 0 ? paragraphs : [text.trim()];
  const units: string[] = [];
  base.forEach((paragraph) => {
    const sentences = paragraph.split(/(?<=[。！？；!?])/).map((item) => item.trim()).filter(Boolean);
    let buffer = "";
    sentences.forEach((sentence) => {
      const candidate = `${buffer} ${sentence}`.trim();
      if (buffer && candidate.length > 220) {
        units.push(buffer);
        buffer = sentence;
      } else {
        buffer = candidate;
      }
    });
    if (buffer) units.push(buffer);
  });
  return units.length > 0 ? units : [text.trim()];
}

function metricBand(value: number, low: number, medium: number, high: number): string {
  if (value >= high) return "高";
  if (value >= medium) return "中";
  if (value >= low) return "低";
  return "待补足";
}

function buildMetricResult(
  id: keyof typeof metricTemplates,
  value: number
): IndicatorMetricResult {
  const template = metricTemplates[id];
  return {
    id,
    name: template.name,
    unit: template.unit,
    value: Number(value.toFixed(2)),
    description: template.description,
    low: template.low,
    medium: template.medium,
    high: template.high,
    band: metricBand(value, template.low, template.medium, template.high)
  };
}

function scoreIndicator(text: string, segments: string[], indicator: IndicatorDefinition): IndicatorScore {
  const matchedKeywords = indicator.keywords.filter((keyword) => text.includes(keyword));
  const keywordHits = indicator.keywords.reduce((sum, keyword) => sum + (text.match(new RegExp(keyword, "g"))?.length ?? 0), 0);
  const segmentHitCount = segments.filter((segment) =>
    indicator.keywords.some((keyword) => segment.includes(keyword))
  ).length;
  const coverage = (segmentHitCount / Math.max(segments.length, 1)) * 100;
  const density = (keywordHits * 1000) / Math.max(text.length, 1);
  const contextBonus = ["教育", "教师", "学生", "课堂", "成长", "社会"].some((keyword) =>
    text.includes(keyword)
  )
    ? 0.08
    : 0;

  const score = Math.min(
    0.96,
    Math.min(1, keywordHits / metricTemplates.keyword_hits.high) * 0.34 +
      Math.min(1, matchedKeywords.length / metricTemplates.cue_diversity.high) * 0.26 +
      Math.min(1, coverage / metricTemplates.segment_coverage.high) * 0.22 +
      Math.min(1, density / metricTemplates.density_per_1000_chars.high) * 0.1 +
      contextBonus
  );

  return {
    id: indicator.id,
    name: indicator.name,
    group_id: indicator.groupId,
    group_name: indicator.groupName,
    aspect_type: indicator.aspectType,
    score: Number(score.toFixed(2)),
    evidence_count: keywordHits,
    matched_keywords: matchedKeywords.slice(0, 8),
    description: indicator.description,
    metric_results: [
      buildMetricResult("keyword_hits", keywordHits),
      buildMetricResult("cue_diversity", matchedKeywords.length),
      buildMetricResult("segment_coverage", coverage),
      buildMetricResult("density_per_1000_chars", density)
    ]
  };
}

function buildGroupScores(indicatorScores: IndicatorScore[]): DimensionScore[] {
  const groups = [
    { id: "natural_personality", name: "自然人格" },
    { id: "professional_personality", name: "职业人格" },
    { id: "moral_personality", name: "道德人格" }
  ];

  return groups.map((group) => {
    const currentItems = indicatorScores.filter((item) => item.group_id === group.id);
    const avgScore =
      currentItems.length > 0
        ? currentItems.reduce((sum, item) => sum + item.score, 0) / currentItems.length
        : 0;
    const topItems = [...currentItems].sort((left, right) => right.score - left.score).slice(0, 2);
    const topScore =
      topItems.length > 0
        ? topItems.reduce((sum, item) => sum + item.score, 0) / topItems.length
        : 0;
    const matchedKeywords = Array.from(
      new Set(currentItems.flatMap((item) => item.matched_keywords))
    ).slice(0, 10);

    return {
      id: group.id,
      name: group.name,
      score: Number(Math.min(0.96, avgScore * 0.42 + topScore * 0.58).toFixed(2)),
      evidence_count: currentItems.reduce((sum, item) => sum + item.evidence_count, 0),
      matched_keywords: matchedKeywords,
      description: groupDescriptions[group.id]
    };
  });
}

function buildSegmentPreviews(text: string): TextSegmentPreview[] {
  const segments = splitTextForAnalysis(text);
  if (segments.length <= 1) return [];
  return segments.map((segment, index) => {
    const result = analyzeTextFallback(segment);
    return {
      index: index + 1,
      excerpt: segment.length > 90 ? `${segment.slice(0, 90)}...` : segment,
      category: result.category,
      level: result.level,
      score: result.score,
      keywords: result.keywords.slice(0, 5)
    };
  });
}

export function analyzeTextFallback(text: string): AnalysisResult {
  const normalizedText = text.trim();
  const segments = splitTextForAnalysis(normalizedText);
  const indicatorScores = indicators
    .map((indicator) => scoreIndicator(normalizedText, segments, indicator))
    .sort((left, right) => right.score - left.score);
  const groupScores = buildGroupScores(indicatorScores).sort((left, right) => right.score - left.score);
  const dominant = groupScores[0];
  const breadth = groupScores.filter((item) => item.score >= 0.26).length;
  const narrativeBonus =
    normalizedText.length >= 1200 ? 0.16 : normalizedText.length >= 400 ? 0.12 : normalizedText.length >= 120 ? 0.08 : 0.04;
  const finalScore = Number(
    Math.min(0.98, dominant.score * 0.82 + Math.max(0, breadth - 1) * 0.05 + narrativeBonus).toFixed(2)
  );
  const level = scoreLevel(finalScore);
  const dominantIndicators = indicatorScores.filter((item) => item.group_id === dominant.id).slice(0, 4);
  const matchedKeywords = Array.from(
    new Set(dominantIndicators.flatMap((item) => item.matched_keywords))
  ).slice(0, 8);
  const isLongText =
    normalizedText.length >= longTextCharThreshold ||
    segments.length >= longTextSegmentThreshold;

  return {
    text: normalizedText,
    text_length: normalizedText.length,
    category: dominant.name,
    level,
    score: finalScore,
    keywords: matchedKeywords,
    rule_reason: matchedKeywords.length
      ? `文本最集中地体现了“${dominant.name}”，主要落在 ${dominantIndicators.map((item) => item.name).join("、")}；线索词包括 ${matchedKeywords.slice(0, 5).join("、")}。`
      : `文本当前更接近论文中的“${dominant.name}”层面，但显式证据仍偏少。`,
    llm_explanation: isLongText
      ? `这是一段较长文本，系统已自动按叙事片段拆分后再汇总分析。整体上它在“${dominant.name}”层面最突出，当前为${level}。`
      : `这段输入在论文对应的“${dominant.name}”层面上最突出，已经能看到较明确的人格特征。`,
    needs_attention: level !== "待补足",
    dominant_dimension_id: dominant.id,
    dimension_scores: groupScores,
    indicator_scores: indicatorScores,
    reference_quotes: referenceQuotes[dominant.id] ?? [],
    score_breakdown: [
      {
        name: "主人格显现度",
        value: Number((dominant.score * 0.82).toFixed(2)),
        description: `当前文本最显著地体现了“${dominant.name}”这一层人格。`
      },
      {
        name: "叙事长度增益",
        value: narrativeBonus,
        description: "较长的叙事或传记材料会带来更丰富的证据密度。"
      }
    ],
    is_long_text: isLongText,
    segment_count: segments.length,
    segment_previews: buildSegmentPreviews(normalizedText)
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
          if (!isValidToken(token)) continue;
          seen.add(token);
        }
      }
    });
    seen.forEach((token) => {
      counts[token] = (counts[token] ?? 0) + 1;
    });
  });

  return Object.entries(counts)
    .sort((left, right) => {
      if (right[1] !== left[1]) return right[1] - left[1];
      if (right[0].length !== left[0].length) return right[0].length - left[0].length;
      return left[0].localeCompare(right[0], "zh-CN");
    })
    .filter(([, count]) => count >= 2)
    .slice(0, 40)
    .map(([keyword, count]) => ({ keyword, count }));
}

function isValidToken(token: string): boolean {
  if (token.length < 2 || stopwords.has(token)) return false;
  if (edgeStopChars.has(token[0]) || edgeStopChars.has(token[token.length - 1])) return false;
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
    high_risk_texts: results.filter((result) => result.needs_attention).slice(0, 10),
    avg_score:
      results.length > 0
        ? Number((results.reduce((sum, item) => sum + item.score, 0) / results.length).toFixed(2))
        : 0
  };
}

export function analyzeBatchFallback(texts: string[]): BatchAnalysisResponse {
  const results = texts.map((text) => analyzeTextFallback(text));
  return {
    summary: buildSummary(results),
    results
  };
}
