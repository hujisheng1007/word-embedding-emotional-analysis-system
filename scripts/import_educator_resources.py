from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.services.research_resource_service import ResearchResourceService, ResourceSchemaNotReady  # noqa: E402


@dataclass(frozen=True)
class Source:
    filename: str
    title: str
    resource_type: str
    educator: str = ""
    authors: tuple[str, ...] = ()


SOURCES = (
    Source("蔡元培画传.docx", "蔡元培画传", "book", educator="蔡元培"),
    Source("蔡元培人物表现_压缩版.txt", "蔡元培人物表现（压缩版）", "note", educator="蔡元培"),
    Source("教育家型教师访谈材料汇总.docx", "教育家型教师访谈材料汇总", "interview"),
    Source(
        "心理学视域下教育家的三重人格：自然、职业与道德_何宁.pdf",
        "心理学视域下教育家的三重人格：自然、职业与道德", "paper", authors=("何宁",),
    ),
)


def main() -> int:
    service = ResearchResourceService()
    completed = 0
    for source in SOURCES:
        try:
            data = (ROOT_DIR / source.filename).read_bytes()
        except OSError as exc:
            print(f"{source.filename}：读取失败（{exc}）", file=sys.stderr)
            continue
        try:
            result = service.import_file(
                filename=source.filename, data=data, title=source.title,
                resource_type=source.resource_type, educator_name=source.educator,
                authors=list(source.authors), citation_text=source.filename,
                access_level="internal", copyright_status="unknown", fulltext_allowed=True,
            )
        except ResourceSchemaNotReady as exc:
            print(exc, file=sys.stderr)
            return 1
        if result.status == "failed":
            print(f"{source.title}：{result.error_message}", file=sys.stderr)
            continue
        detail = service.get_resource(result.resource_id)
        if detail is None or not detail.segments:
            print(f"{source.title}：已有记录，但没有可检索的正文。", file=sys.stderr)
            continue
        completed += 1
        status = "已导入" if result.status == "succeeded" else "已存在"
        print(f"{source.title} | {status} | {len(detail.segments)} 段 | {result.resource_id}")
    return int(completed != len(SOURCES))


if __name__ == "__main__":
    sys.exit(main())
