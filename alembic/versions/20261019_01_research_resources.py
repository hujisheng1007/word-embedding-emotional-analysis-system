"""add research resource library tables

Revision ID: 20261019_01
Revises:
Create Date: 2026-10-19
"""

from alembic import op
import sqlalchemy as sa


revision = "20261019_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "educator_persons",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("aliases_json", sa.Text(), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("death_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_educator_persons_display_name", "educator_persons", ["display_name"])

    op.create_table(
        "research_resources",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("source_institution", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("collected_at", sa.DateTime(), nullable=False),
        sa.Column("file_format", sa.String(length=32), nullable=False),
        sa.Column("copyright_status", sa.String(length=64), nullable=False),
        sa.Column("fulltext_allowed", sa.Boolean(), nullable=False),
        sa.Column("access_level", sa.String(length=32), nullable=False),
        sa.Column("original_locator", sa.Text(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("educator_person_id", sa.String(length=36), nullable=True),
        sa.Column("analysis_status", sa.String(length=32), nullable=False),
        sa.Column("data_version", sa.String(length=64), nullable=False),
        sa.Column("citation_text", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["educator_person_id"], ["educator_persons.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "title",
        "resource_type",
        "copyright_status",
        "access_level",
        "educator_person_id",
        "analysis_status",
        "content_sha256",
    ):
        op.create_index(f"ix_research_resources_{column}", "research_resources", [column])

    op.create_table(
        "resource_authors",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("resource_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("organization", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["resource_id"], ["research_resources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_resource_authors_resource_id", "resource_authors", ["resource_id"])
    op.create_index("ix_resource_authors_name", "resource_authors", ["name"])

    op.create_table(
        "resource_files",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("resource_id", sa.String(length=36), nullable=False),
        sa.Column("original_name", sa.String(length=500), nullable=False),
        sa.Column("stored_name", sa.String(length=255), nullable=False),
        sa.Column("stored_path", sa.Text(), nullable=False),
        sa.Column("media_type", sa.String(length=255), nullable=False),
        sa.Column("extension", sa.String(length=32), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("parse_status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["resource_id"], ["research_resources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_resource_files_resource_id", "resource_files", ["resource_id"])
    op.create_index("ix_resource_files_sha256", "resource_files", ["sha256"], unique=True)
    op.create_index("ix_resource_files_parse_status", "resource_files", ["parse_status"])

    op.create_table(
        "resource_segments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("resource_id", sa.String(length=36), nullable=False),
        sa.Column("resource_file_id", sa.String(length=36), nullable=True),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("locator_type", sa.String(length=32), nullable=False),
        sa.Column("locator_value", sa.String(length=255), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("text_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["resource_file_id"], ["resource_files.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resource_id"], ["research_resources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resource_id", "ordinal", name="uq_resource_segment_ordinal"),
    )
    op.create_index("ix_resource_segments_resource_id", "resource_segments", ["resource_id"])
    op.create_index("ix_resource_segments_resource_file_id", "resource_segments", ["resource_file_id"])
    op.create_index("ix_resource_segments_text_sha256", "resource_segments", ["text_sha256"])

    op.create_table(
        "resource_import_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("file_name", sa.String(length=500), nullable=False),
        sa.Column("file_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("resource_id", sa.String(length=36), nullable=True),
        sa.Column("duplicate_of_resource_id", sa.String(length=36), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["resource_id"], ["research_resources.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_resource_import_jobs_file_sha256", "resource_import_jobs", ["file_sha256"])
    op.create_index("ix_resource_import_jobs_status", "resource_import_jobs", ["status"])
    op.create_index("ix_resource_import_jobs_resource_id", "resource_import_jobs", ["resource_id"])


def downgrade() -> None:
    op.drop_table("resource_import_jobs")
    op.drop_table("resource_segments")
    op.drop_table("resource_files")
    op.drop_table("resource_authors")
    op.drop_table("research_resources")
    op.drop_table("educator_persons")
