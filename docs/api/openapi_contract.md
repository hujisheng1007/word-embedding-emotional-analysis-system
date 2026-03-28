# API Contract

## `POST /api/analyze`

请求体：

```json
{
  "text": "最近真的要崩溃了，不想继续了",
  "mode": "hybrid"
}
```

响应体：

```json
{
  "text": "最近真的要崩溃了，不想继续了",
  "category": "心理风险",
  "level": "高",
  "score": 0.91,
  "keywords": ["崩溃", "不想继续"],
  "rule_reason": "命中极端消极表达词，并伴随明显绝望倾向短语",
  "llm_explanation": "文本包含强烈消极和绝望表达，建议人工重点关注。",
  "needs_attention": true
}
```

## `POST /api/analyze/batch`

请求体：

```json
{
  "texts": [
    "最近真的要崩溃了，不想继续了",
    "这个学校处理问题太离谱了，我要发到网上曝光",
    "今天天气不错，课也很顺利"
  ],
  "mode": "hybrid"
}
```

响应体结构：

```json
{
  "summary": {
    "total": 3,
    "category_distribution": {
      "心理风险": 1,
      "舆情风险": 1,
      "正常文本": 1
    },
    "level_distribution": {
      "高": 1,
      "中": 1,
      "正常": 1
    },
    "top_keywords": [
      { "keyword": "崩溃", "count": 1 },
      { "keyword": "学校", "count": 1 }
    ],
    "attention_count": 2,
    "high_risk_texts": []
  },
  "results": []
}
```
