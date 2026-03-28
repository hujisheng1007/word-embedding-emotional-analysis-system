import type { BatchAnalysisResponse } from "../types/analysis";

export const dashboardMockData: BatchAnalysisResponse = {
  summary: {
    total: 6,
    category_distribution: {
      心理风险: 2,
      舆情风险: 1,
      一般负面: 2,
      正常文本: 1
    },
    level_distribution: {
      高: 2,
      中: 1,
      低: 2,
      正常: 1
    },
    top_keywords: [
      { keyword: "崩溃", count: 2 },
      { keyword: "学校", count: 1 },
      { keyword: "曝光", count: 1 },
      { keyword: "难受", count: 1 },
      { keyword: "累", count: 1 }
    ],
    attention_count: 3,
    high_risk_texts: [
      {
        text: "最近真的要崩溃了，不想继续了。",
        category: "心理风险",
        level: "高",
        score: 0.92,
        keywords: ["崩溃", "不想继续"],
        rule_reason: "命中心理高风险关键词，规则层判定为优先关注对象。",
        llm_explanation: "文本包含明显极端消极和绝望表达，建议优先人工复核。",
        needs_attention: true
      },
      {
        text: "这个学校处理问题太离谱了，我要发到网上曝光。",
        category: "舆情风险",
        level: "中",
        score: 0.76,
        keywords: ["学校", "曝光", "离谱"],
        rule_reason: "命中校园舆情相关词，并伴随负面或扩散倾向表达。",
        llm_explanation: "文本含有较强负面评价或公开扩散倾向，存在舆情传播风险。",
        needs_attention: true
      }
    ]
  },
  results: [
    {
      text: "最近真的要崩溃了，不想继续了。",
      category: "心理风险",
      level: "高",
      score: 0.92,
      keywords: ["崩溃", "不想继续"],
      rule_reason: "命中心理高风险关键词，规则层判定为优先关注对象。",
      llm_explanation: "文本包含明显极端消极和绝望表达，建议优先人工复核。",
      needs_attention: true
    },
    {
      text: "这个学校处理问题太离谱了，我要发到网上曝光。",
      category: "舆情风险",
      level: "中",
      score: 0.76,
      keywords: ["学校", "曝光", "离谱"],
      rule_reason: "命中校园舆情相关词，并伴随负面或扩散倾向表达。",
      llm_explanation: "文本含有较强负面评价或公开扩散倾向，存在舆情传播风险。",
      needs_attention: true
    },
    {
      text: "今天事情好多，真的有点累。",
      category: "一般负面",
      level: "低",
      score: 0.43,
      keywords: ["累"],
      rule_reason: "命中一般负面情绪词，但未达到高风险触发条件。",
      llm_explanation: "文本带有一定消极情绪，建议结合上下文继续观察。",
      needs_attention: false
    },
    {
      text: "这周压力有点大，心里挺难受。",
      category: "一般负面",
      level: "低",
      score: 0.43,
      keywords: ["难受"],
      rule_reason: "命中一般负面情绪词，但未达到高风险触发条件。",
      llm_explanation: "文本带有一定消极情绪，建议结合上下文继续观察。",
      needs_attention: false
    },
    {
      text: "不想活了，感觉一切都没有意义。",
      category: "心理风险",
      level: "高",
      score: 0.92,
      keywords: ["不想活了"],
      rule_reason: "命中心理高风险关键词，规则层判定为优先关注对象。",
      llm_explanation: "文本包含明显极端消极和绝望表达，建议优先人工复核。",
      needs_attention: true
    },
    {
      text: "今天天气不错，课也很顺利。",
      category: "正常文本",
      level: "正常",
      score: 0.08,
      keywords: [],
      rule_reason: "未命中明显风险规则。",
      llm_explanation: "当前文本整体为正常表达。",
      needs_attention: false
    }
  ]
};
