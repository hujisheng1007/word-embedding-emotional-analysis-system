from __future__ import annotations

import re
from collections import Counter

from app.schemas.analysis import KeywordCount


CHINESE_BLOCK_PATTERN = re.compile(r"[\u4e00-\u9fff]{2,}")
COMMON_STOPWORDS = {
    "我们",
    "你们",
    "他们",
    "她们",
    "自己",
    "一个",
    "这个",
    "那个",
    "不是",
    "然后",
    "因为",
    "所以",
    "就是",
    "还有",
    "如果",
    "的话",
    "时候",
    "觉得",
    "可能",
    "现在",
    "已经",
    "没有",
    "这样",
    "一些",
    "很多",
    "这种",
    "那个时候",
    "这个时候",
    "比较",
    "可以",
    "一种",
    "什么",
    "怎么",
    "对于",
    "以及",
    "但是",
    "进行",
    "之后",
    "之前",
    "后来",
    "还是",
    "这些",
    "应该",
    "比如",
    "感觉",
    "方面",
    "能够",
    "问题",
    "工作",
    "其实",
    "我们都",
}
EDGE_STOP_CHARS = set("的了一是在和与及就都也很把让对给将被向从到地得着而并但或其我个这那")


def extract_wordcloud_keywords(
    texts: list[str],
    *,
    limit: int = 40,
    min_count: int = 2,
) -> list[KeywordCount]:
    counter: Counter[str] = Counter()

    for text in texts:
        seen_in_text: set[str] = set()
        for block in CHINESE_BLOCK_PATTERN.findall(text):
            max_n = min(4, len(block))
            for n in range(2, max_n + 1):
                for start in range(0, len(block) - n + 1):
                    token = block[start:start + n]
                    if _is_valid_token(token):
                        seen_in_text.add(token)
        counter.update(seen_in_text)

    selected: list[tuple[str, int]] = []
    ranked_items = sorted(counter.items(), key=lambda item: (-item[1], -len(item[0]), item[0]))
    for token, count in ranked_items:
        if count < min_count:
            continue
        if any(token in chosen and count <= chosen_count for chosen, chosen_count in selected):
            continue
        selected.append((token, count))
        if len(selected) >= limit:
            break

    return [KeywordCount(keyword=token, count=count) for token, count in selected]


def _is_valid_token(token: str) -> bool:
    if len(token) < 2 or token in COMMON_STOPWORDS:
        return False
    if token[0] in EDGE_STOP_CHARS or token[-1] in EDGE_STOP_CHARS:
        return False
    if len(set(token)) == 1:
        return False
    return True
