from __future__ import annotations

import re

import httpx

from app.core.settings import get_settings


class LLMEngine:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def enabled(self) -> bool:
        return self.settings.llm_enabled

    def generate_explanation(
        self,
        *,
        text: str,
        category: str,
        level: str,
        keywords: list[str],
        rule_reason: str,
        fallback: str | None = None,
    ) -> str | None:
        if not self.enabled:
            return fallback

        safe_fallback = fallback or self._build_basic_fallback(
            category=category,
            level=level,
            keywords=keywords,
            rule_reason=rule_reason,
        )

        raw_text = self._request_completion(
            messages=self._build_messages(
                text=text,
                category=category,
                level=level,
                keywords=keywords,
                rule_reason=rule_reason,
                fallback=safe_fallback,
            ),
            temperature=0.15,
            max_tokens=72,
        )
        sanitized = self._sanitize_output(
            raw_text=raw_text,
            fallback=safe_fallback,
            category=category,
            keywords=keywords,
        )
        if sanitized != safe_fallback:
            return sanitized

        repaired_text = self._request_completion(
            messages=self._build_repair_messages(
                text=text,
                category=category,
                level=level,
                fallback=safe_fallback,
            ),
            temperature=0.2,
            max_tokens=56,
        )
        return self._sanitize_output(
            raw_text=repaired_text,
            fallback=safe_fallback,
            category=category,
            keywords=keywords,
        )

    def _request_completion(
        self,
        *,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        response = httpx.post(
            f"{self.settings.llm_base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.settings.llm_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.settings.llm_model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "messages": messages,
            },
            timeout=self.settings.llm_timeout,
        )
        response.raise_for_status()
        payload = response.json()
        return str(payload["choices"][0]["message"]["content"]).strip()

    def _build_messages(
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
                    "你是校园文本分析系统的解释助手。"
                    "你的任务不是重新分类，而是把现有结果改写成一句适合老师、辅导员或行政人员查看的自然中文提示。"
                    "只输出一句中文解释，不要输出标题、标签、项目符号、Markdown、提示词、system、user、category、level 等字段。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"原始文本：{text}\n"
                    f"当前类别：{category}\n"
                    f"当前等级：{level}\n"
                    f"命中关键词：{keyword_text}\n"
                    f"规则依据：{rule_reason}\n"
                    f"可参考解释：{fallback}\n\n"
                    "请生成一句更自然、更适合界面展示的解释。"
                    "不要照抄原文，不要新增事实，不要输出任何提示语或字段名。"
                ),
            },
        ]

    def _build_repair_messages(
        self,
        *,
        text: str,
        category: str,
        level: str,
        fallback: str,
    ) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": (
                    "你是校园文本分析系统的润色助手。"
                    "请将给定说明改写成一句自然、简洁、适合界面展示的中文解释。"
                    "不要输出提示语，不要复述任务说明，不要添加额外判断。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"文本：{text}\n"
                    f"类别：{category}\n"
                    f"等级：{level}\n"
                    f"候选解释：{fallback}\n\n"
                    "请直接输出一句最终解释。"
                ),
            },
        ]

    def _sanitize_output(
        self,
        *,
        raw_text: str,
        fallback: str,
        category: str,
        keywords: list[str],
    ) -> str:
        text = self._normalize_text(raw_text)
        if not text:
            return fallback

        candidates = self._extract_candidates(text)
        for candidate in candidates:
            if self._is_valid_explanation(candidate, category=category, keywords=keywords):
                return candidate

        return fallback

    def _normalize_text(self, raw_text: str) -> str:
        text = raw_text.replace("\r", "\n")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{2,}", "\n", text)
        return text.strip().strip('"').strip("'").strip()

    def _extract_candidates(self, text: str) -> list[str]:
        lines = [self._clean_candidate(line) for line in text.split("\n")]
        candidates = [line for line in lines if line]
        if candidates:
            return candidates

        segments = re.split(r"(?<=[。！？])", text)
        return [self._clean_candidate(segment) for segment in segments if self._clean_candidate(segment)]

    def _clean_candidate(self, candidate: str) -> str:
        cleaned = candidate.strip()
        cleaned = re.sub(r"^[#>*\-\d\.\)\s]+", "", cleaned)
        cleaned = cleaned.strip("：: ")
        cleaned = cleaned.strip('"').strip("'").strip()
        return cleaned

    def _is_valid_explanation(
        self,
        text: str,
        *,
        category: str,
        keywords: list[str],
    ) -> bool:
        lowered = text.lower()
        banned_fragments = [
            "请只输出",
            "最终一句解释",
            "候选解释",
            "规则依据",
            "规则说明",
            "原始文本",
            "当前类别",
            "当前等级",
            "命中关键词",
            "可参考解释",
            "字段名",
            "system",
            "user",
            "assistant",
            "category",
            "level",
            "markdown",
            "输入第一行",
            "接下来",
            "每行一个文本",
            "表示文本总数",
            "请注意",
            "辅助人工审核",
            "不能作为最终结果",
        ]
        if not text or len(text) < 12 or len(text) > 64:
            return False
        if any(fragment in text or fragment in lowered for fragment in banned_fragments):
            return False
        if text.count("请") >= 2:
            return False
        if text.startswith("输出") or text.startswith("解释"):
            return False
        if category not in text and keywords:
            keyword_hits = sum(1 for keyword in keywords if keyword in text)
            if keyword_hits == 0 and len(text) < 12:
                return False
        return True

    def _build_basic_fallback(
        self,
        *,
        category: str,
        level: str,
        keywords: list[str],
        rule_reason: str,
    ) -> str:
        if category == "心理风险":
            return f"文本呈现较明显的极端消极表达，当前判定为{level}风险，建议尽快人工关注。"
        if category == "舆情风险":
            return f"文本涉及校园相关负面扩散倾向，当前判定为{level}舆情风险，建议持续关注。"
        if category == "一般负面":
            return "文本表现出一定负面情绪，但暂未达到高风险触发条件。"
        return "文本整体表达较为日常平稳，当前未发现明显风险信号。"
