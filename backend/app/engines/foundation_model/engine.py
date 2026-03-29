from __future__ import annotations

import json
import re
from dataclasses import dataclass

import httpx

from app.services.foundation_profile_service import get_foundation_profile_service


VALID_CATEGORIES = {"心理风险", "舆情风险", "一般负面", "正常文本"}
VALID_LEVELS = {"高", "中", "低", "正常"}


@dataclass(frozen=True)
class FoundationModelPrediction:
    category: str
    level: str
    score: float
    reason: str


class FoundationModelEngine:
    def __init__(self) -> None:
        self.profile_service = get_foundation_profile_service()

    @property
    def enabled(self) -> bool:
        return self.profile_service.get_runtime_config().enabled

    def predict(self, text: str) -> FoundationModelPrediction | None:
        runtime = self.profile_service.get_runtime_config()
        if not runtime.enabled:
            return None

        raw_text = self._request_completion(
            runtime=runtime,
            messages=self._build_prediction_messages(text),
            temperature=0.1,
            max_tokens=220,
        )
        return self._parse_prediction(raw_text)

    def generate_explanation(
        self,
        *,
        text: str,
        category: str,
        level: str,
        keywords: list[str],
        rule_reason: str,
        fallback: str,
    ) -> str | None:
        runtime = self.profile_service.get_runtime_config()
        if not runtime.enabled:
            return None

        raw_text = self._request_completion(
            runtime=runtime,
            messages=self._build_explanation_messages(
                text=text,
                category=category,
                level=level,
                keywords=keywords,
                rule_reason=rule_reason,
                fallback=fallback,
            ),
            temperature=0.25,
            max_tokens=90,
        )
        return self._sanitize_explanation(raw_text, fallback=fallback)

    def _request_completion(
        self,
        *,
        runtime,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        response = httpx.post(
            f"{runtime.base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {runtime.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": runtime.model_name,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "messages": messages,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        payload = response.json()
        return str(payload["choices"][0]["message"]["content"]).strip()

    def _build_prediction_messages(self, text: str) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": (
                    "你是校园文本情感与风险研判助手。"
                    "请只输出一个 JSON 对象，不要输出任何额外说明。"
                    "category 只能是：心理风险、舆情风险、一般负面、正常文本。"
                    "level 只能是：高、中、低、正常。"
                    "score 是 0 到 1 之间的小数。"
                    "reason 是一句中文分析依据。"
                    "你需要结合上下文、隐含含义、谐音梗、缩写、网络黑话、阴阳怪气、反讽和隐晦表达来判断，"
                    "不能只看显式关键词。"
                    "不要因为出现学校、老师等校园词就直接判为舆情风险，"
                    "只有同时出现明显负面扩散、对抗、投诉、曝光、举报、发帖、挂人等倾向时才判为舆情风险。"
                ),
            },
            {
                "role": "user",
                "content": (
                    '{"category":"正常文本","level":"正常","score":0.12,"reason":"一句中文分析依据"}\n'
                    f"待分析文本：{text}"
                ),
            },
        ]

    def _build_explanation_messages(
        self,
        *,
        text: str,
        category: str,
        level: str,
        keywords: list[str],
        rule_reason: str,
        fallback: str,
    ) -> list[dict[str, str]]:
        keyword_text = "、".join(keywords) if keywords else "无明显关键词"
        return [
            {
                "role": "system",
                "content": (
                    "你是给学校老师、辅导员和行政人员使用的校园文本研判助手。"
                    "请输出一句自然、克制、专业、适合管理人员查看的中文说明。"
                    "不要像聊天，不要像安慰，不要像模板。"
                    "不要出现“重点词包括”“当前文本整体为”“建议持续关注后续表述”这类空泛句式。"
                    "要直接说明这段话为什么被判为当前类别，语气要客观。"
                    "不要输出标题、字段名、Markdown 或提示词。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"原始文本：{text}\n"
                    f"当前类别：{category}\n"
                    f"当前等级：{level}\n"
                    f"显式线索：{keyword_text}\n"
                    f"规则依据：{rule_reason}\n"
                    f"候选说明：{fallback}\n\n"
                    "请生成一句更贴合这条文本的说明。"
                    "如果是正常文本，要明确说明它更像咨询、求助、日常表达还是信息交换。"
                    "如果是风险文本，要明确指出风险是来自情绪强度、扩散倾向、极端表达还是隐含攻击性。"
                ),
            },
        ]

    def _parse_prediction(self, raw_text: str) -> FoundationModelPrediction | None:
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if not match:
            return None

        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None

        category = str(payload.get("category", "")).strip()
        level = str(payload.get("level", "")).strip()
        reason = str(payload.get("reason", "")).strip() or "大模型给出了分类判断。"

        if category not in VALID_CATEGORIES or level not in VALID_LEVELS:
            return None

        try:
            score = float(payload.get("score", 0.5))
        except (TypeError, ValueError):
            score = 0.5

        score = min(1.0, max(0.0, score))
        return FoundationModelPrediction(
            category=category,
            level=level,
            score=score,
            reason=reason,
        )

    def _sanitize_explanation(self, raw_text: str, *, fallback: str) -> str:
        text = raw_text.replace("\r", "\n").strip()
        lines = [line.strip().strip('"').strip("'") for line in text.split("\n") if line.strip()]
        banned_fragments = [
            "请生成",
            "候选说明",
            "规则依据",
            "原始文本",
            "当前类别",
            "当前等级",
            "显式线索",
            "重点词包括",
            "当前文本整体为",
            "建议持续关注后续表述",
            "markdown",
            "system",
            "user",
            "输入第一行",
            "接下来",
            "每行一个文本",
            "表示文本总数",
            "请注意",
            "辅助人工审核",
            "不能作为最终结果",
        ]
        for line in lines:
            lowered = line.lower()
            if len(line) < 12 or len(line) > 72:
                continue
            if any(fragment in line or fragment in lowered for fragment in banned_fragments):
                continue
            return line
        return fallback
