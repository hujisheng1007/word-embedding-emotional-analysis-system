import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class RuleDefinition:
    category: str
    level: str
    score: float
    keywords: tuple[str, ...]
    trigger_groups: tuple[tuple[str, ...], ...]
    rule_reason: str
    llm_explanation: str


BASE_DIR = Path(__file__).resolve().parent
RULES_FILE = BASE_DIR / "rules.json"


@lru_cache(maxsize=1)
def get_rule_definitions() -> tuple[RuleDefinition, ...]:
    payload = json.loads(RULES_FILE.read_text(encoding="utf-8"))
    return tuple(
        RuleDefinition(
            category=item["category"],
            level=item["level"],
            score=item["score"],
            keywords=tuple(item["keywords"]),
            trigger_groups=tuple(tuple(group) for group in item.get("trigger_groups", [])),
            rule_reason=item["rule_reason"],
            llm_explanation=item["llm_explanation"],
        )
        for item in payload["rules"]
    )


@lru_cache(maxsize=1)
def get_default_result() -> RuleDefinition:
    payload = json.loads(RULES_FILE.read_text(encoding="utf-8"))
    item = payload["default"]
    return RuleDefinition(
        category=item["category"],
        level=item["level"],
        score=item["score"],
        keywords=tuple(item["keywords"]),
        trigger_groups=tuple(tuple(group) for group in item.get("trigger_groups", [])),
        rule_reason=item["rule_reason"],
        llm_explanation=item["llm_explanation"],
    )
