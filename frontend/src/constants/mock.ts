import type { BatchAnalysisResponse, MetricBenchmark, ReferenceLibraryResponse } from "../types/analysis";

const metricBenchmarks: MetricBenchmark[] = [
  {
    id: "keyword_hits",
    name: "关键词命中数",
    unit: "次",
    description: "直接相关线索词的命中次数。",
    low: 1,
    medium: 3,
    high: 6
  },
  {
    id: "cue_diversity",
    name: "线索多样度",
    unit: "项",
    description: "命中的不同线索词数量。",
    low: 1,
    medium: 2,
    high: 4
  },
  {
    id: "segment_coverage",
    name: "段落覆盖率",
    unit: "%",
    description: "命中线索的分段占比。",
    low: 15,
    medium: 35,
    high: 60
  },
  {
    id: "density_per_1000_chars",
    name: "千字证据密度",
    unit: "次/千字",
    description: "按文本长度归一化后的证据密度。",
    low: 2,
    medium: 5,
    high: 9
  }
];

export const referenceLibraryMockData: ReferenceLibraryResponse = {
  source_name: "教育家三重人格底库",
  source_file: "educator_interviews_import.csv",
  total_excerpts: 669,
  total_respondents: 24,
  dimensions: [
    {
      id: "natural_personality",
      name: "自然人格",
      description: "先行基础，关注稳定积极的情绪内核、成长取向和面对挑战时的心理韧性。",
      question_ids: ["Q1", "Q2", "Q5", "Q8", "Q16", "Q17"],
      keyword_cues: ["稳定", "热爱", "成长", "学习", "调节", "探索"],
      excerpt_count: 236,
      indicators: [
        {
          id: "emotional_stability",
          name: "情绪稳定",
          aspect_type: "quality",
          description: "面对压力、挫折和复杂情境时保持平和、坚韧与可持续投入。",
          question_ids: ["Q5", "Q8", "Q16"],
          keyword_cues: ["稳定", "情绪", "压力", "调节", "坚韧"],
          metric_benchmarks: metricBenchmarks
        },
        {
          id: "active_learning_behavior",
          name: "主动学习行为",
          aspect_type: "behavior",
          description: "主动阅读、进修、借鉴经验并把学习转化为实践更新。",
          question_ids: ["Q4", "Q8", "Q17"],
          keyword_cues: ["阅读", "进修", "学习", "更新", "尝试"],
          metric_benchmarks: metricBenchmarks
        }
      ],
      highlight_terms: [
        { keyword: "热爱", count: 15 },
        { keyword: "学习", count: 13 },
        { keyword: "成长", count: 12 }
      ],
      sample_quotes: [
        {
          respondent_name: "访谈教师A",
          question_id: "Q1",
          question: "您是什么契机选择成为一名教师的？",
          text: "对教育的热爱和稳定的内在信念，是支撑我持续走下去的根本动力。"
        }
      ]
    },
    {
      id: "professional_personality",
      name: "职业人格",
      description: "现实依托，关注教学智慧、师生互动、专业精进和职业行动力。",
      question_ids: ["Q3", "Q4", "Q6", "Q7", "Q14"],
      keyword_cues: ["课堂", "教学", "学生", "反馈", "反思", "沟通"],
      excerpt_count: 248,
      indicators: [
        {
          id: "teaching_wisdom",
          name: "教学机敏",
          aspect_type: "quality",
          description: "课堂组织、策略切换、因材施教与临场判断能力。",
          question_ids: ["Q6", "Q7", "Q14"],
          keyword_cues: ["课堂", "教学", "反馈", "策略", "设计"],
          metric_benchmarks: metricBenchmarks
        },
        {
          id: "classroom_design_behavior",
          name: "课堂设计行为",
          aspect_type: "behavior",
          description: "通过项目、活动、反馈和节奏安排把育人意图落到课堂结构上。",
          question_ids: ["Q6", "Q7", "Q14"],
          keyword_cues: ["设计", "项目", "活动", "反馈", "任务"],
          metric_benchmarks: metricBenchmarks
        }
      ],
      highlight_terms: [
        { keyword: "课堂", count: 20 },
        { keyword: "学生", count: 18 },
        { keyword: "反馈", count: 9 }
      ],
      sample_quotes: [
        {
          respondent_name: "访谈教师B",
          question_id: "Q6",
          question: "面对学生和家长的挑战，您认为优秀教师应如何应对？",
          text: "如果教师愿意在课堂设计、沟通方式和反馈节奏上持续调整，很多问题会被化解。"
        }
      ]
    },
    {
      id: "moral_personality",
      name: "道德人格",
      description: "根本支撑，关注使命感、利他精神、文化担当与社会价值取向。",
      question_ids: ["Q9", "Q10", "Q11", "Q12", "Q13", "Q15"],
      keyword_cues: ["使命", "奉献", "担当", "文化", "社会", "价值"],
      excerpt_count: 185,
      indicators: [
        {
          id: "self_transcendence",
          name: "使命超越",
          aspect_type: "quality",
          description: "超越个人功利的小我，转向使命、意义与更高价值追求。",
          question_ids: ["Q9", "Q11", "Q12", "Q13"],
          keyword_cues: ["使命", "意义", "超越", "价值", "大我"],
          metric_benchmarks: metricBenchmarks
        },
        {
          id: "ethical_action_behavior",
          name: "道德践履行为",
          aspect_type: "behavior",
          description: "把价值判断转化为真实选择、示范行动与长期承担。",
          question_ids: ["Q12", "Q13", "Q15"],
          keyword_cues: ["践行", "示范", "选择", "行动", "影响"],
          metric_benchmarks: metricBenchmarks
        }
      ],
      highlight_terms: [
        { keyword: "使命", count: 12 },
        { keyword: "奉献", count: 10 },
        { keyword: "担当", count: 8 }
      ],
      sample_quotes: [
        {
          respondent_name: "访谈教师C",
          question_id: "Q13",
          question: "您认为教育家对教育事业的推动作用体现在哪些方面？",
          text: "教育家真正重要的不是个人成就，而是能否把价值和方向感带给更多人。"
        }
      ]
    }
  ]
};

export const dashboardMockData: BatchAnalysisResponse = {
  summary: {
    total: 3,
    category_distribution: {
      自然人格: 1,
      职业人格: 1,
      道德人格: 1
    },
    level_distribution: {
      高显现: 1,
      中显现: 1,
      初显现: 1
    },
    top_keywords: [
      { keyword: "课堂", count: 2 },
      { keyword: "学生", count: 2 },
      { keyword: "成长", count: 1 }
    ],
    wordcloud_keywords: [
      { keyword: "课堂", count: 2 },
      { keyword: "学生", count: 2 },
      { keyword: "反馈", count: 1 },
      { keyword: "成长", count: 1 }
    ],
    attention_count: 3,
    high_risk_texts: [],
    avg_score: 0.74
  },
  results: [
    {
      text: "教师只有先让自己保持稳定、热爱和持续学习，才能真正影响学生。",
      text_length: 34,
      category: "自然人格",
      level: "中显现",
      score: 0.69,
      keywords: ["稳定", "热爱", "学习", "学生"],
      rule_reason: "文本最集中地体现了“自然人格”，主要落在 情绪稳定、乐教热情、开放成长；线索词包括 稳定、热爱、学习、学生。",
      llm_explanation: "这段输入在论文对应的“自然人格”层面上最突出，已显现较明确的情绪内核与成长取向。",
      needs_attention: true,
      dominant_dimension_id: "natural_personality",
      dimension_scores: [
        {
          id: "natural_personality",
          name: "自然人格",
          score: 0.71,
          evidence_count: 7,
          matched_keywords: ["稳定", "热爱", "学习", "学生"],
          description: "先行基础，关注稳定积极的情绪内核、成长取向和面对挑战时的心理韧性。"
        }
      ],
      indicator_scores: [
        {
          id: "emotional_stability",
          name: "情绪稳定",
          group_id: "natural_personality",
          group_name: "自然人格",
          aspect_type: "quality",
          score: 0.62,
          evidence_count: 2,
          matched_keywords: ["稳定"],
          description: "面对压力、挫折和复杂情境时保持平和、坚韧与可持续投入。",
          metric_results: [
            { id: "keyword_hits", name: "关键词命中数", unit: "次", value: 2, description: "直接相关线索词的命中次数。", low: 1, medium: 3, high: 6, band: "低" },
            { id: "cue_diversity", name: "线索多样度", unit: "项", value: 1, description: "命中的不同线索词数量。", low: 1, medium: 2, high: 4, band: "低" },
            { id: "segment_coverage", name: "段落覆盖率", unit: "%", value: 100, description: "命中线索的分段占比。", low: 15, medium: 35, high: 60, band: "高" },
            { id: "density_per_1000_chars", name: "千字证据密度", unit: "次/千字", value: 58.8, description: "按文本长度归一化后的证据密度。", low: 2, medium: 5, high: 9, band: "高" }
          ]
        }
      ],
      reference_quotes: ["对教育的热爱和稳定的内在信念，是支撑我持续走下去的根本动力。"],
      is_long_text: false,
      segment_count: 1,
      segment_previews: []
    },
    {
      text: "我会把课堂反馈和项目实践都放进教学设计里，让学生在真实任务中成长。",
      text_length: 36,
      category: "职业人格",
      level: "高显现",
      score: 0.84,
      keywords: ["课堂", "反馈", "项目", "设计", "学生"],
      rule_reason: "文本最集中地体现了“职业人格”，主要落在 教学机敏、课堂设计行为、师生亲和；线索词包括 课堂、反馈、项目、设计、学生。",
      llm_explanation: "这段输入在论文对应的“职业人格”层面上最突出，能看到明确的教学实施路径。",
      needs_attention: true,
      dominant_dimension_id: "professional_personality",
      dimension_scores: [
        {
          id: "professional_personality",
          name: "职业人格",
          score: 0.79,
          evidence_count: 10,
          matched_keywords: ["课堂", "反馈", "项目", "设计", "学生"],
          description: "现实依托，关注教学智慧、师生互动、专业精进和职业行动力。"
        }
      ],
      indicator_scores: [
        {
          id: "classroom_design_behavior",
          name: "课堂设计行为",
          group_id: "professional_personality",
          group_name: "职业人格",
          aspect_type: "behavior",
          score: 0.88,
          evidence_count: 4,
          matched_keywords: ["课堂", "反馈", "项目", "设计"],
          description: "通过项目、活动、反馈和节奏安排把育人意图落到课堂结构上。",
          metric_results: [
            { id: "keyword_hits", name: "关键词命中数", unit: "次", value: 4, description: "直接相关线索词的命中次数。", low: 1, medium: 3, high: 6, band: "中" },
            { id: "cue_diversity", name: "线索多样度", unit: "项", value: 4, description: "命中的不同线索词数量。", low: 1, medium: 2, high: 4, band: "高" },
            { id: "segment_coverage", name: "段落覆盖率", unit: "%", value: 100, description: "命中线索的分段占比。", low: 15, medium: 35, high: 60, band: "高" },
            { id: "density_per_1000_chars", name: "千字证据密度", unit: "次/千字", value: 111.1, description: "按文本长度归一化后的证据密度。", low: 2, medium: 5, high: 9, band: "高" }
          ]
        }
      ],
      reference_quotes: ["如果教师愿意在课堂设计、沟通方式和反馈节奏上持续调整，很多问题会被化解。"],
      is_long_text: false,
      segment_count: 1,
      segment_previews: []
    },
    {
      text: "他早年从乡村学校起步，在长期办学中不断强调教师要先修己、再育人；后来面对社会转型，他反复提出教育不仅是知识训练，更是文化传承与公共责任。即便在最艰难的阶段，他仍坚持资助贫困学生、推动课程改革，并把个人荣誉看得很轻，总说教育者要把更多光亮留给后来者。",
      text_length: 134,
      category: "道德人格",
      level: "中显现",
      score: 0.76,
      keywords: ["文化", "责任", "坚持", "学生", "教育者"],
      rule_reason: "文本最集中地体现了“道德人格”，主要落在 使命超越、社会担当、道德践履行为；线索词包括 文化、责任、坚持、学生、教育者。",
      llm_explanation: "这是一段较长文本，系统已自动按叙事片段拆分后再汇总分析。整体上它在“道德人格”层面最突出，当前为中显现。",
      needs_attention: true,
      dominant_dimension_id: "moral_personality",
      dimension_scores: [
        {
          id: "moral_personality",
          name: "道德人格",
          score: 0.73,
          evidence_count: 9,
          matched_keywords: ["文化", "责任", "坚持", "学生", "教育者"],
          description: "根本支撑，关注使命感、利他精神、文化担当与社会价值取向。"
        }
      ],
      indicator_scores: [
        {
          id: "collective_commitment",
          name: "社会担当",
          group_id: "moral_personality",
          group_name: "道德人格",
          aspect_type: "quality",
          score: 0.81,
          evidence_count: 3,
          matched_keywords: ["文化", "责任"],
          description: "将教育与国家、社会、文化和集体责任联系起来的担当意识。",
          metric_results: [
            { id: "keyword_hits", name: "关键词命中数", unit: "次", value: 3, description: "直接相关线索词的命中次数。", low: 1, medium: 3, high: 6, band: "中" },
            { id: "cue_diversity", name: "线索多样度", unit: "项", value: 2, description: "命中的不同线索词数量。", low: 1, medium: 2, high: 4, band: "中" },
            { id: "segment_coverage", name: "段落覆盖率", unit: "%", value: 50, description: "命中线索的分段占比。", low: 15, medium: 35, high: 60, band: "中" },
            { id: "density_per_1000_chars", name: "千字证据密度", unit: "次/千字", value: 22.39, description: "按文本长度归一化后的证据密度。", low: 2, medium: 5, high: 9, band: "高" }
          ]
        }
      ],
      reference_quotes: ["教育家真正重要的不是个人成就，而是能否把价值和方向感带给更多人。"],
      is_long_text: true,
      segment_count: 2,
      segment_previews: [
        {
          index: 1,
          excerpt: "他早年从乡村学校起步，在长期办学中不断强调教师要先修己、再育人；后来面对社会转型，他反复提出教育不仅是知识训练，更是文化传承与公共责任。",
          category: "道德人格",
          level: "中显现",
          score: 0.71,
          keywords: ["文化", "责任", "教育"]
        },
        {
          index: 2,
          excerpt: "即便在最艰难的阶段，他仍坚持资助贫困学生、推动课程改革，并把个人荣誉看得很轻，总说教育者要把更多光亮留给后来者。",
          category: "道德人格",
          level: "初显现",
          score: 0.62,
          keywords: ["坚持", "学生", "教育者"]
        }
      ]
    }
  ]
};

dashboardMockData.summary.high_risk_texts = dashboardMockData.results.filter((item) => item.needs_attention);
