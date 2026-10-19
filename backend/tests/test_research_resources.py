from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from pypdf import PdfWriter
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.api.routes import research_resources as resource_routes
from app.db.base import Base
from app.db import research_models  # noqa: F401
from app.main import app
from app.services.research_resource_service import (
    ResearchResourceService,
    ResourceSchemaNotReady,
)
from app.services.resource_parsers import ResourceParseError, parse_resource


@pytest.fixture()
def resource_service(tmp_path: Path) -> ResearchResourceService:
    engine = create_engine(f"sqlite:///{(tmp_path / 'resources.db').as_posix()}", future=True)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return ResearchResourceService(factory, tmp_path / "stored")


def test_fulltext_import_is_traceable_and_deduplicated(resource_service: ResearchResourceService) -> None:
    content = "第一段：教育是一项长期事业。\n\n第二段：教师需要持续反思。".encode()
    first = resource_service.import_file(
        filename="../访谈.txt",
        data=content,
        media_type="text/plain",
        title="教育访谈",
        resource_type="interview",
        authors=["研究者甲", "研究者甲"],
        educator_name="示例教育家",
        copyright_status="authorized",
        fulltext_allowed=True,
        access_level="internal",
    )
    assert first.status == "succeeded"
    assert first.segment_count == 2
    assert first.resource_id

    detail = resource_service.get_resource(first.resource_id)
    assert detail is not None
    assert detail.educator_name == "示例教育家"
    assert detail.author_names == ["研究者甲"]
    assert detail.segments[0].locator_type == "paragraph"
    assert detail.segments[0].locator_value == "1"
    assert detail.files[0].original_name == "访谈.txt"
    assert detail.files[0].original_retained is True
    assert "第一段" in detail.extracted_text

    duplicate = resource_service.import_file(
        filename="另一名称.txt",
        data=content,
        resource_type="interview",
        copyright_status="authorized",
        fulltext_allowed=True,
    )
    assert duplicate.status == "duplicate"
    assert duplicate.duplicate_of_resource_id == first.resource_id
    assert resource_service.get_stats().total == 1
    assert [job.status for job in resource_service.list_jobs()] == ["duplicate", "succeeded"]


def test_metadata_only_import_does_not_retain_text_or_original(resource_service: ResearchResourceService) -> None:
    result = resource_service.import_file(
        filename="paper.txt",
        data=b"private full text",
        resource_type="paper",
        copyright_status="unknown",
        fulltext_allowed=False,
    )
    assert result.status == "succeeded"
    detail = resource_service.get_resource(result.resource_id or "")
    assert detail is not None
    assert detail.extracted_text == ""
    assert detail.segments == []
    assert detail.files[0].parse_status == "metadata_only"
    assert detail.files[0].original_retained is False
    assert not resource_service.storage_root.exists()


def test_subtitle_parser_keeps_timestamps() -> None:
    segments = parse_resource(
        "lecture.srt",
        b"1\n00:00:01,000 --> 00:00:03,000\nOpening line\n\n2\n00:00:04,000 --> 00:00:06,000\nSecond line\n",
    )
    assert [segment.locator_type for segment in segments] == ["timestamp", "timestamp"]
    assert segments[0].locator_value == "00:00:01,000-->00:00:03,000"


def test_repeated_text_keeps_each_source_location() -> None:
    segments = parse_resource("repeat.txt", "相同证据\n\n相同证据".encode())
    assert [segment.locator_value for segment in segments] == ["1", "2"]


def test_csv_json_docx_and_xlsx_parsers_keep_source_locators() -> None:
    csv_segments = parse_resource("rows.csv", "text,category\n第一行,A\n第二行,B\n".encode())
    assert [(item.locator_type, item.locator_value) for item in csv_segments] == [("row", "2"), ("row", "3")]

    json_segments = parse_resource("notes.json", json.dumps({"items": [{"content": "一条 JSON 内容"}]}).encode())
    assert json_segments[0].locator_value == "$.items[0].content"

    docx_buffer = io.BytesIO()
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:p><w:r><w:t>DOCX 段落</w:t></w:r></w:p></w:body></w:document>"
    )
    with zipfile.ZipFile(docx_buffer, "w") as archive:
        archive.writestr("word/document.xml", document_xml)
    docx_segments = parse_resource("document.docx", docx_buffer.getvalue())
    assert docx_segments[0].locator_type == "paragraph"
    assert docx_segments[0].text == "DOCX 段落"

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "资料"
    worksheet.append(["标题", "正文"])
    worksheet.append(["样例", "XLSX 内容"])
    xlsx_buffer = io.BytesIO()
    workbook.save(xlsx_buffer)
    xlsx_segments = parse_resource("sheet.xlsx", xlsx_buffer.getvalue())
    assert xlsx_segments[1].locator_value == "资料!2"


def test_image_only_pdf_reports_ocr_requirement() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    buffer = io.BytesIO()
    writer.write(buffer)
    with pytest.raises(ResourceParseError, match="OCR"):
        parse_resource("scan.pdf", buffer.getvalue())


def test_restricted_copyright_rejects_fulltext(resource_service: ResearchResourceService) -> None:
    result = resource_service.import_file(
        filename="restricted.txt",
        data=b"content",
        copyright_status="restricted",
        fulltext_allowed=True,
    )
    assert result.status == "failed"
    assert "不能保存全文" in result.error_message
    assert resource_service.list_jobs()[0].status == "failed"


def test_missing_migration_returns_clear_error(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{(tmp_path / 'empty.db').as_posix()}", future=True)
    factory = sessionmaker(bind=engine, future=True)
    service = ResearchResourceService(factory, tmp_path / "stored")
    with pytest.raises(ResourceSchemaNotReady, match="alembic upgrade head"):
        service.get_stats()


def test_resource_api_import_list_and_detail(
    resource_service: ResearchResourceService, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(resource_routes, "service", resource_service)
    client = TestClient(app)
    response = client.post(
        "/api/research-resources/import",
        files={"files": ("notes.txt", "第一段\n\n第二段", "text/plain")},
        data={
            "resource_type": "note",
            "copyright_status": "authorized",
            "fulltext_allowed": "true",
            "access_level": "internal",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["succeeded"] == 1
    resource_id = payload["results"][0]["resource_id"]

    list_response = client.get("/api/research-resources", params={"keyword": "notes"})
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    detail_response = client.get(f"/api/research-resources/{resource_id}")
    assert detail_response.status_code == 200
    assert len(detail_response.json()["segments"]) == 2
