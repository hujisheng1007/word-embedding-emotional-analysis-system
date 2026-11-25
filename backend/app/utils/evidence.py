def resolve_quote(
    source: str, quote: str, start: int | None, end: int | None
) -> tuple[int, int]:
    """Resolve a literal quotation using Unicode code-point offsets."""
    if start is None or end is None:
        start = source.find(quote)
        if start < 0 or source.find(quote, start + 1) >= 0:
            raise ValueError("引文不存在或重复位置不明确，请指定精确字符范围")
        end = start + len(quote)
    if not quote.strip() or not 0 <= start < end <= len(source) or source[start:end] != quote:
        raise ValueError("引文与原文字符范围不一致")
    return start, end
