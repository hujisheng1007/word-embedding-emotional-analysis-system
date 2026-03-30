from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricBenchmarkDefinition:
    id: str
    name: str
    unit: str
    description: str
    low: float
    medium: float
    high: float


@dataclass(frozen=True)
class EducatorGroupDefinition:
    id: str
    name: str
    description: str
    question_ids: tuple[str, ...]


@dataclass(frozen=True)
class EducatorIndicatorDefinition:
    id: str
    name: str
    group_id: str
    aspect_type: str
    description: str
    question_ids: tuple[str, ...]
    cue_keywords: tuple[str, ...]


INDICATOR_METRIC_BENCHMARKS: tuple[MetricBenchmarkDefinition, ...] = (
    MetricBenchmarkDefinition(
        id="keyword_hits",
        name="关键词命中数",
        unit="次",
        description="文本中与该品质或行为直接相关的线索词命中次数。",
        low=1,
        medium=3,
        high=6,
    ),
    MetricBenchmarkDefinition(
        id="cue_diversity",
        name="线索多样度",
        unit="项",
        description="命中的不同线索词数量，反映品质是否有多面呈现。",
        low=1,
        medium=2,
        high=4,
    ),
    MetricBenchmarkDefinition(
        id="segment_coverage",
        name="段落覆盖率",
        unit="%",
        description="命中线索的分段占全部分段的比例，长文本时尤其有参考意义。",
        low=15,
        medium=35,
        high=60,
    ),
    MetricBenchmarkDefinition(
        id="density_per_1000_chars",
        name="千字证据密度",
        unit="次/千字",
        description="按文本长度归一化后的证据密度，便于比较短文本与长传记。",
        low=2,
        medium=5,
        high=9,
    ),
)


EDUCATOR_GROUPS: tuple[EducatorGroupDefinition, ...] = (
    EducatorGroupDefinition(
        id="natural_personality",
        name="自然人格",
        description="先行基础，关注教育者稳定积极的情绪内核、成长取向和面对挑战时的心理韧性。",
        question_ids=("Q1", "Q2", "Q5", "Q8", "Q16", "Q17"),
    ),
    EducatorGroupDefinition(
        id="professional_personality",
        name="职业人格",
        description="现实依托，关注教学智慧、师生互动、专业精进和职业行动力。",
        question_ids=("Q3", "Q4", "Q6", "Q7", "Q14"),
    ),
    EducatorGroupDefinition(
        id="moral_personality",
        name="道德人格",
        description="根本支撑，关注使命感、利他精神、文化担当与社会价值取向。",
        question_ids=("Q9", "Q10", "Q11", "Q12", "Q13", "Q15"),
    ),
)


EDUCATOR_INDICATORS: tuple[EducatorIndicatorDefinition, ...] = (
    EducatorIndicatorDefinition(
        id="emotional_stability",
        name="情绪稳定",
        group_id="natural_personality",
        aspect_type="quality",
        description="面对压力、挫折和复杂情境时保持平和、坚韧与可持续投入。",
        question_ids=("Q5", "Q8", "Q16"),
        cue_keywords=("稳定", "情绪", "压力", "调节", "从容", "坚韧", "平和", "乐观", "倦怠"),
    ),
    EducatorIndicatorDefinition(
        id="intrinsic_motivation",
        name="乐教热情",
        group_id="natural_personality",
        aspect_type="quality",
        description="对教育事业具有持续热爱、内在动力和职业信念。",
        question_ids=("Q1", "Q2", "Q5"),
        cue_keywords=("热爱", "热情", "喜欢", "信念", "动力", "乐教", "初心", "理想", "愿望"),
    ),
    EducatorIndicatorDefinition(
        id="open_growth",
        name="开放成长",
        group_id="natural_personality",
        aspect_type="quality",
        description="愿意学习、接纳变化、持续更新经验并主动尝试新路径。",
        question_ids=("Q4", "Q8", "Q17"),
        cue_keywords=("开放", "学习", "探索", "变化", "更新", "尝试", "接纳", "成长", "好奇"),
    ),
    EducatorIndicatorDefinition(
        id="self_regulation_behavior",
        name="自我调节行为",
        group_id="natural_personality",
        aspect_type="behavior",
        description="出现困难时主动调节节奏、修复状态并保持稳定行动。",
        question_ids=("Q5", "Q16"),
        cue_keywords=("调整", "调节", "修复", "缓解", "坚持", "应对", "处理", "恢复"),
    ),
    EducatorIndicatorDefinition(
        id="active_learning_behavior",
        name="主动学习行为",
        group_id="natural_personality",
        aspect_type="behavior",
        description="主动阅读、进修、借鉴经验并把学习转化为实践更新。",
        question_ids=("Q4", "Q8", "Q17"),
        cue_keywords=("阅读", "进修", "学习", "更新", "借鉴", "反思", "积累", "尝试"),
    ),
    EducatorIndicatorDefinition(
        id="teaching_wisdom",
        name="教学机敏",
        group_id="professional_personality",
        aspect_type="quality",
        description="课堂组织、策略切换、因材施教与临场判断能力。",
        question_ids=("Q6", "Q7", "Q14"),
        cue_keywords=("课堂", "教学", "备课", "反馈", "因材施教", "策略", "设计", "组织", "机智", "方法"),
    ),
    EducatorIndicatorDefinition(
        id="student_affinity",
        name="师生亲和",
        group_id="professional_personality",
        aspect_type="quality",
        description="理解学生与家长、建立信任并形成温暖互动关系的能力。",
        question_ids=("Q3", "Q6"),
        cue_keywords=("学生", "家长", "沟通", "理解", "尊重", "陪伴", "关爱", "倾听", "亲和", "回应"),
    ),
    EducatorIndicatorDefinition(
        id="professional_perseverance",
        name="专业精进",
        group_id="professional_personality",
        aspect_type="quality",
        description="长期投入、反思改进、提升效能并持续深耕专业。",
        question_ids=("Q4", "Q5", "Q14"),
        cue_keywords=("坚持", "精进", "反思", "专业", "笃行", "积累", "效能", "长期", "成长", "改进"),
    ),
    EducatorIndicatorDefinition(
        id="classroom_design_behavior",
        name="课堂设计行为",
        group_id="professional_personality",
        aspect_type="behavior",
        description="通过项目、活动、反馈和节奏安排把育人意图落到课堂结构上。",
        question_ids=("Q6", "Q7", "Q14"),
        cue_keywords=("设计", "项目", "活动", "任务", "反馈", "节奏", "结构", "课堂"),
    ),
    EducatorIndicatorDefinition(
        id="communication_coordination_behavior",
        name="沟通协同行为",
        group_id="professional_personality",
        aspect_type="behavior",
        description="与学生、家长、同事协同沟通，化解问题并形成教育合力。",
        question_ids=("Q3", "Q6", "Q14"),
        cue_keywords=("沟通", "协调", "合作", "家长", "同事", "支持", "回应", "协同"),
    ),
    EducatorIndicatorDefinition(
        id="self_transcendence",
        name="使命超越",
        group_id="moral_personality",
        aspect_type="quality",
        description="超越个人功利的小我，转向使命、意义与更高价值追求。",
        question_ids=("Q9", "Q11", "Q12", "Q13"),
        cue_keywords=("大我", "使命", "意义", "超越", "理想", "召唤", "弘道", "价值", "追求"),
    ),
    EducatorIndicatorDefinition(
        id="altruistic_care",
        name="利他关怀",
        group_id="moral_personality",
        aspect_type="quality",
        description="以学生为先、乐教爱生、甘于奉献并愿意成全他人。",
        question_ids=("Q6", "Q12", "Q15"),
        cue_keywords=("奉献", "利他", "爱生", "仁爱", "关怀", "无私", "学生为先", "成全", "温度"),
    ),
    EducatorIndicatorDefinition(
        id="collective_commitment",
        name="社会担当",
        group_id="moral_personality",
        aspect_type="quality",
        description="将教育与国家、社会、文化和集体责任联系起来的担当意识。",
        question_ids=("Q10", "Q13", "Q15", "Q17"),
        cue_keywords=("国家", "社会", "文化", "天下", "担当", "责任", "强国", "文明", "集体", "引领"),
    ),
    EducatorIndicatorDefinition(
        id="ethical_action_behavior",
        name="道德践履行为",
        group_id="moral_personality",
        aspect_type="behavior",
        description="把价值判断转化为真实选择、示范行动与长期承担。",
        question_ids=("Q12", "Q13", "Q15"),
        cue_keywords=("践行", "示范", "选择", "坚持", "担当", "行动", "带动", "影响"),
    ),
    EducatorIndicatorDefinition(
        id="cultural_guidance_behavior",
        name="文化引领行为",
        group_id="moral_personality",
        aspect_type="behavior",
        description="把教育与文化传承、社会方向和文明建构联系起来。",
        question_ids=("Q10", "Q13", "Q15", "Q17"),
        cue_keywords=("文化", "传承", "弘道", "天下", "方向", "引领", "文明", "社会"),
    ),
)


def get_group_definition_map() -> dict[str, EducatorGroupDefinition]:
    return {item.id: item for item in EDUCATOR_GROUPS}
