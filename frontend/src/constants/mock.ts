import type { BatchAnalysisResponse } from "../types/analysis";

export const dashboardMockData: BatchAnalysisResponse = {
  summary: {
    total: 6,
    category_distribution: {
      心理风险: 1,
      舆情风险: 1,
      一般负面: 2,
      正常文本: 2
    },
    level_distribution: {
      高: 1,
      中: 1,
      低: 2,
      正常: 2
    },
    top_keywords: [
      { keyword: "崩溃", count: 1 },
      { keyword: "曝光", count: 1 },
      { keyword: "难受", count: 1 },
      { keyword: "压力", count: 1 }
    ],
    wordcloud_keywords: [
      { keyword: "学生", count: 3 },
      { keyword: "老师", count: 3 },
      { keyword: "情绪", count: 2 },
      { keyword: "成长", count: 2 },
      { keyword: "沟通", count: 2 },
      { keyword: "崩溃", count: 1 },
      { keyword: "曝光", count: 1 },
      { keyword: "压力", count: 1 },
      { keyword: "难受", count: 1 },
      { keyword: "课堂", count: 1 },
      { keyword: "反馈", count: 1 },
      { keyword: "理解", count: 1 }
    ],
    attention_count: 2,
    high_risk_texts: [
      {
        text: "最近真的快撑不住了，整个人特别崩溃。",
        category: "一般负面",
        level: "低",
        score: 0.43,
        keywords: ["崩溃"],
        rule_reason: "命中一般负面情绪词，但未达到高风险触发条件。",
        llm_explanation: "文本体现出明显压力与负面情绪，建议结合上下文继续观察。",
        needs_attention: false
      },
      {
        text: "这个学校处理投诉的方式太离谱了，我准备发帖曝光。",
        category: "舆情风险",
        level: "中",
        score: 0.76,
        keywords: ["学校", "投诉", "离谱", "发帖", "曝光"],
        rule_reason: "文本同时出现校园对象和负面扩散倾向表达，存在舆情传播风险。",
        llm_explanation: "文本对校园相关对象表达了较强负面评价，并伴随扩散倾向，建议重点关注。",
        needs_attention: true
      }
    ]
  },
  results: [
    {
      text: "最近真的快撑不住了，整个人特别崩溃。",
      category: "一般负面",
      level: "低",
      score: 0.43,
      keywords: ["崩溃"],
      rule_reason: "命中一般负面情绪词，但未达到高风险触发条件。",
      llm_explanation: "文本体现出明显压力与负面情绪，建议结合上下文继续观察。",
      needs_attention: false
    },
    {
      text: "这个学校处理投诉的方式太离谱了，我准备发帖曝光。",
      category: "舆情风险",
      level: "中",
      score: 0.76,
      keywords: ["学校", "投诉", "离谱", "发帖", "曝光"],
      rule_reason: "文本同时出现校园对象和负面扩散倾向表达，存在舆情传播风险。",
      llm_explanation: "文本对校园相关对象表达了较强负面评价，并伴随扩散倾向，建议重点关注。",
      needs_attention: true
    },
    {
      text: "这周事情太多了，备课和开会压得我有点难受。",
      category: "一般负面",
      level: "低",
      score: 0.43,
      keywords: ["压力", "难受"],
      rule_reason: "命中一般负面情绪词，但未达到高风险触发条件。",
      llm_explanation: "文本体现出一定负面情绪，建议结合上下文继续观察。",
      needs_attention: false
    },
    {
      text: "今天和学生谈完之后感觉轻松多了，课堂状态也不错。",
      category: "正常文本",
      level: "正常",
      score: 0.08,
      keywords: [],
      rule_reason: "未命中明显风险规则。",
      llm_explanation: "当前文本整体为日常表达。",
      needs_attention: false
    },
    {
      text: "有学生明确说自己不想活了，这条需要马上关注。",
      category: "心理风险",
      level: "高",
      score: 0.92,
      keywords: ["不想活了"],
      rule_reason: "命中心理高风险强触发表达，规则层判定为优先关注对象。",
      llm_explanation: "文本包含明显的极端消极或自伤倾向表达，建议优先人工复核。",
      needs_attention: true
    },
    {
      text: "这次家长反馈比较积极，班级整体状态也比较稳定。",
      category: "正常文本",
      level: "正常",
      score: 0.08,
      keywords: [],
      rule_reason: "未命中明显风险规则。",
      llm_explanation: "当前文本整体为日常表达。",
      needs_attention: false
    }
  ]
};
