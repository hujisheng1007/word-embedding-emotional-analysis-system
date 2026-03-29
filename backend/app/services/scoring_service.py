from __future__ import annotations

from dataclasses import dataclass

from app.schemas.analysis import ScoreFactor


BASE_SCORES = {
    "心理风险": 0.68,
    "舆情风险": 0.46,
    "一般负面": 0.28,
    "正常文本": 0.06,
}

INTENSIFIERS = (
    "很",
    "太",
    "非常",
    "特别",
    "真的",
    "一直",
    "极其",
    "简直",
    "越来越",
    "根本",
    "完全",
    "顶不住",
    "受不了",
    "离谱",
    "炸了",
    "崩溃",
)
HELP_SEEKING_WORDS = (
    "求助",
    "请问",
    "想问",
    "有没有",
    "学长学姐",
    "有人知道",
    "怎么样",
    "如何",
)
SUSTAINED_WORDS = (
    "一直",
    "总是",
    "最近",
    "这段时间",
    "长期",
    "每天",
    "反复",
)
RELIEF_WORDS = (
    "顺利",
    "不错",
    "挺好",
    "轻松",
    "解决了",
    "没事",
    "稳定",
    "积极",
    "感谢",
    "谢谢",
)
NEGATIVE_WORDS = (
    "难受",
    "压力",
    "焦虑",
    "烦",
    "烦躁",
    "委屈",
    "失落",
    "痛苦",
    "崩溃",
    "不开心",
    "压抑",
    "难熬",
)
PSYCHOLOGY_WORDS = (
    "不想活了",
    "活不下去",
    "结束自己",
    "结束生命",
    "轻生",
    "自杀",
    "没有活着的意义",
    "不如死了",
)
FIRST_PERSON_WORDS = ("我", "自己", "本人")
CAMPUS_OBJECT_WORDS = (
    "学校",
    "学院",
    "宿舍",
    "食堂",
    "老师",
    "辅导员",
    "课程",
    "招生",
    "管理",
    "校园",
)
PUBLIC_ACTION_WORDS = (
    "投诉",
    "曝光",
    "维权",
    "举报",
    "发帖",
    "热搜",
    "扩散",
    "转发",
    "挂网上",
    "闹大",
)
CONFRONTATION_WORDS = (
    "离谱",
    "垃圾",
    "推诿",
    "不作为",
    "过分",
    "恶心",
)
URGENCY_WORDS = ("马上", "立刻", "现在", "今晚", "今天", "尽快")


@dataclass(frozen=True)
class ScoreResult:
    score: float
    level: str
    breakdown: list[ScoreFactor]


class ScoringService:
    def score_text(
        self,
        *,
        text: str,
        category: str,
        keywords: list[str],
        model_score: float | None = None,
    ) -> ScoreResult:
        heuristic_breakdown: list[ScoreFactor] = []
        heuristic_total = BASE_SCORES.get(category, 0.08)
        self._append_factor(
            heuristic_breakdown,
            name="基础分",
            value=heuristic_total,
            description=f"根据当前类别“{category}”给出初始风险基线。",
        )

        keyword_value = min(
            0.16,
            len(keywords) * 0.03 + sum(0.01 for keyword in keywords if len(keyword) >= 3),
        )
        self._append_factor(
            heuristic_breakdown,
            name="显式线索",
            value=keyword_value,
            description=f"根据当前文本中可明确识别的关键词或风险线索进行加权。",
        )
        heuristic_total += keyword_value

        intensity_hits = self._count_hits(text, INTENSIFIERS) + min(
            text.count("!") + text.count("！") + text.count("?") + text.count("？"),
            2,
        )
        intensity_value = min(0.12, intensity_hits * 0.02)
        self._append_factor(
            heuristic_breakdown,
            name="情绪强度",
            value=intensity_value,
            description="根据语气词、强调词和标点强度估计表达激烈程度。",
        )
        heuristic_total += intensity_value

        if category == "心理风险":
            heuristic_total += self._score_psychology(text, heuristic_breakdown)
        elif category == "舆情风险":
            heuristic_total += self._score_public_opinion(text, heuristic_breakdown)
        elif category == "一般负面":
            heuristic_total += self._score_negative(text, heuristic_breakdown)
        else:
            heuristic_total += self._score_normal(text, heuristic_breakdown)

        relief_hits = self._count_hits(text, RELIEF_WORDS)
        relief_value = -min(0.08, relief_hits * 0.025)
        self._append_factor(
            heuristic_breakdown,
            name="缓和信息",
            value=relief_value,
            description="如果文本同时包含缓和、解决或积极表达，会适度下调风险分。",
        )
        heuristic_total += relief_value
        heuristic_total = min(0.99, max(0.02, heuristic_total))

        if model_score is None:
            final_score = round(heuristic_total, 2)
            return ScoreResult(
                score=final_score,
                level=self._level_from_score(category=category, score=final_score),
                breakdown=heuristic_breakdown,
            )

        model_anchor = min(0.99, max(0.02, model_score))
        model_weight = 0.68
        heuristic_weight = 0.32
        final_score = round(model_anchor * model_weight + heuristic_total * heuristic_weight, 2)

        breakdown: list[ScoreFactor] = [
            ScoreFactor(
                name="模型语义研判",
                value=round(model_anchor * model_weight, 2),
                description="由当前选中的大模型结合上下文、隐含语义、网络表达和谐音梗等信息给出的主评分依据。",
            ),
            ScoreFactor(
                name="规则与文本线索",
                value=round(heuristic_total * heuristic_weight, 2),
                description="由显式关键词、情绪强度、扩散倾向、缓和信息等可解释线索提供的辅助评分。",
            ),
        ]
        breakdown.extend(heuristic_breakdown[:4])

        return ScoreResult(
            score=final_score,
            level=self._level_from_score(category=category, score=final_score),
            breakdown=breakdown,
        )

    def _score_psychology(self, text: str, breakdown: list[ScoreFactor]) -> float:
        value = 0.0
        self_harm_hits = self._count_hits(text, PSYCHOLOGY_WORDS)
        self_harm_value = min(0.18, self_harm_hits * 0.08)
        self._append_factor(
            breakdown,
            name="极端自伤表达",
            value=self_harm_value,
            description="识别是否存在明显的自伤、自杀或失去生存意愿表达。",
        )
        value += self_harm_value

        self_ref_value = 0.05 if self._count_hits(text, FIRST_PERSON_WORDS) > 0 else 0.0
        self._append_factor(
            breakdown,
            name="自我指向",
            value=self_ref_value,
            description="第一人称叙述通常意味着表达更直接地指向个体自身状态。",
        )
        value += self_ref_value

        urgency_value = 0.04 if self._count_hits(text, URGENCY_WORDS) > 0 else 0.0
        self._append_factor(
            breakdown,
            name="紧迫程度",
            value=urgency_value,
            description="带有立即性、当下性词语时，上调关注优先级。",
        )
        value += urgency_value
        return value

    def _score_public_opinion(self, text: str, breakdown: list[ScoreFactor]) -> float:
        value = 0.0
        campus_hits = self._count_hits(text, CAMPUS_OBJECT_WORDS)
        campus_value = min(0.08, campus_hits * 0.02)
        self._append_factor(
            breakdown,
            name="校园对象相关",
            value=campus_value,
            description="文本明确指向学校、学院、宿舍、老师等校园对象。",
        )
        value += campus_value

        spread_hits = self._count_hits(text, PUBLIC_ACTION_WORDS)
        spread_value = min(0.16, spread_hits * 0.04)
        self._append_factor(
            breakdown,
            name="扩散/行动倾向",
            value=spread_value,
            description="根据投诉、曝光、发帖、举报、扩散等行动词提升舆情风险分。",
        )
        value += spread_value

        confrontation_hits = self._count_hits(text, CONFRONTATION_WORDS)
        confrontation_value = min(0.1, confrontation_hits * 0.03)
        self._append_factor(
            breakdown,
            name="对抗语气",
            value=confrontation_value,
            description="负面评价越尖锐，对舆情扩散的放大作用越强。",
        )
        value += confrontation_value
        return value

    def _score_negative(self, text: str, breakdown: list[ScoreFactor]) -> float:
        value = 0.0
        negative_hits = self._count_hits(text, NEGATIVE_WORDS)
        negative_value = min(0.16, negative_hits * 0.035)
        self._append_factor(
            breakdown,
            name="负面情绪浓度",
            value=negative_value,
            description="根据压力、焦虑、难受、崩溃等表述提升一般负面得分。",
        )
        value += negative_value

        sustained_hits = self._count_hits(text, SUSTAINED_WORDS)
        sustained_value = min(0.08, sustained_hits * 0.03)
        self._append_factor(
            breakdown,
            name="持续性表达",
            value=sustained_value,
            description="最近、长期、反复等词语说明情绪可能并非瞬时波动。",
        )
        value += sustained_value

        help_hits = self._count_hits(text, HELP_SEEKING_WORDS)
        help_value = -min(0.04, help_hits * 0.02)
        self._append_factor(
            breakdown,
            name="求助语境",
            value=help_value,
            description="如果更像求助或咨询而非宣泄，会轻微下调风险分。",
        )
        value += help_value
        return value

    def _score_normal(self, text: str, breakdown: list[ScoreFactor]) -> float:
        value = 0.0
        help_hits = self._count_hits(text, HELP_SEEKING_WORDS)
        help_value = min(0.05, help_hits * 0.02)
        self._append_factor(
            breakdown,
            name="求助/咨询语境",
            value=help_value,
            description="日常求助、提问或经验咨询会让正常文本分数略有浮动，但仍保持低风险。",
        )
        value += help_value

        negative_hits = self._count_hits(text, NEGATIVE_WORDS)
        mild_negative_value = min(0.04, negative_hits * 0.015)
        self._append_factor(
            breakdown,
            name="轻微负面信号",
            value=mild_negative_value,
            description="若存在少量轻微负面表述，会给正常文本增加一点观察分。",
        )
        value += mild_negative_value
        return value

    def _count_hits(self, text: str, words: tuple[str, ...]) -> int:
        return sum(1 for word in words if word in text)

    def _append_factor(
        self,
        breakdown: list[ScoreFactor],
        *,
        name: str,
        value: float,
        description: str,
    ) -> None:
        if abs(value) < 0.005:
            return
        breakdown.append(
            ScoreFactor(
                name=name,
                value=round(value, 2),
                description=description,
            )
        )

    def _level_from_score(self, *, category: str, score: float) -> str:
        if category == "心理风险":
            if score >= 0.8:
                return "高"
            if score >= 0.68:
                return "中"
            return "低"
        if category == "舆情风险":
            if score >= 0.8:
                return "高"
            if score >= 0.56:
                return "中"
            return "低"
        if category == "一般负面":
            if score >= 0.62:
                return "中"
            return "低"
        return "正常"
