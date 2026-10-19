"""add multi-source collection center

Revision ID: 20261019_02
Revises: 20261019_01
Create Date: 2026-10-19
"""

from alembic import op
import sqlalchemy as sa


revision = "20261019_02"
down_revision = "20261019_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "collection_sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("adapter_key", sa.String(64), nullable=False),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("terms_url", sa.Text(), nullable=False),
        sa.Column("robots_url", sa.Text(), nullable=False),
        sa.Column("license_note", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("allows_metadata", sa.Boolean(), nullable=False),
        sa.Column("allows_subtitles", sa.Boolean(), nullable=False),
        sa.Column("allows_media_download", sa.Boolean(), nullable=False),
        sa.Column("allows_transcription", sa.Boolean(), nullable=False),
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=False),
        sa.Column("schedule_interval_minutes", sa.Integer(), nullable=False),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_collection_sources_adapter_key", "collection_sources", ["adapter_key"], unique=True)
    op.create_index("ix_collection_sources_source_type", "collection_sources", ["source_type"])

    op.create_table(
        "collection_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_id", sa.String(36), nullable=False),
        sa.Column("job_type", sa.String(64), nullable=False),
        sa.Column("query_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("total_count", sa.Integer(), nullable=False),
        sa.Column("success_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("duplicate_count", sa.Integer(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("pause_requested", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["source_id"], ["collection_sources.id"], ondelete="RESTRICT"),
    )
    for column in ("source_id", "job_type", "status"):
        op.create_index(f"ix_collection_jobs_{column}", "collection_jobs", [column])

    op.create_table(
        "collection_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), nullable=False),
        sa.Column("level", sa.String(16), nullable=False),
        sa.Column("event", sa.String(64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("context_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["collection_jobs.id"], ondelete="CASCADE"),
    )
    for column in ("job_id", "level", "event"):
        op.create_index(f"ix_collection_logs_{column}", "collection_logs", [column])

    op.create_table(
        "resource_identifiers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("resource_id", sa.String(36), nullable=False),
        sa.Column("scheme", sa.String(64), nullable=False),
        sa.Column("value", sa.String(500), nullable=False),
        sa.ForeignKeyConstraint(["resource_id"], ["research_resources.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("scheme", "value", name="uq_resource_identifier"),
    )
    op.create_index("ix_resource_identifiers_resource_id", "resource_identifiers", ["resource_id"])
    op.create_index("ix_resource_identifiers_scheme", "resource_identifiers", ["scheme"])

    op.create_table(
        "person_external_identities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("person_id", sa.String(36), nullable=False),
        sa.Column("source_key", sa.String(64), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("review_status", sa.String(32), nullable=False),
        sa.Column("raw_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["person_id"], ["educator_persons.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("source_key", "external_id", name="uq_person_external_identity"),
    )
    for column in ("person_id", "source_key", "review_status"):
        op.create_index(f"ix_person_external_identities_{column}", "person_external_identities", [column])

    op.create_table(
        "person_facts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("person_id", sa.String(36), nullable=False),
        sa.Column("resource_id", sa.String(36), nullable=True),
        sa.Column("fact_type", sa.String(64), nullable=False),
        sa.Column("value_text", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_title", sa.String(500), nullable=False),
        sa.Column("source_publisher", sa.String(255), nullable=False),
        sa.Column("review_status", sa.String(32), nullable=False),
        sa.Column("extracted_by", sa.String(64), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["person_id"], ["educator_persons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resource_id"], ["research_resources.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("person_id", "content_sha256", name="uq_person_fact_content"),
    )
    for column in ("person_id", "resource_id", "fact_type", "review_status"):
        op.create_index(f"ix_person_facts_{column}", "person_facts", [column])

    op.create_table(
        "video_assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("resource_id", sa.String(36), nullable=False),
        sa.Column("platform", sa.String(64), nullable=False),
        sa.Column("external_id", sa.String(500), nullable=False),
        sa.Column("page_url", sa.Text(), nullable=False),
        sa.Column("embed_url", sa.Text(), nullable=False),
        sa.Column("media_url", sa.Text(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("license_code", sa.String(128), nullable=False),
        sa.Column("license_url", sa.Text(), nullable=False),
        sa.Column("embed_allowed", sa.Boolean(), nullable=False),
        sa.Column("subtitle_access", sa.Boolean(), nullable=False),
        sa.Column("download_allowed", sa.Boolean(), nullable=False),
        sa.Column("transcription_allowed", sa.Boolean(), nullable=False),
        sa.Column("restriction_reason", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("collected_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["resource_id"], ["research_resources.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("platform", "external_id", name="uq_video_asset_external"),
    )
    op.create_index("ix_video_assets_resource_id", "video_assets", ["resource_id"], unique=True)
    op.create_index("ix_video_assets_platform", "video_assets", ["platform"])

    op.create_table(
        "transcripts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("resource_id", sa.String(36), nullable=False),
        sa.Column("video_asset_id", sa.String(36), nullable=True),
        sa.Column("language", sa.String(32), nullable=False),
        sa.Column("origin", sa.String(32), nullable=False),
        sa.Column("model_name", sa.String(128), nullable=False),
        sa.Column("model_version", sa.String(128), nullable=False),
        sa.Column("review_status", sa.String(32), nullable=False),
        sa.Column("full_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["resource_id"], ["research_resources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["video_asset_id"], ["video_assets.id"], ondelete="CASCADE"),
    )
    for column in ("resource_id", "video_asset_id", "origin", "review_status"):
        op.create_index(f"ix_transcripts_{column}", "transcripts", [column])

    op.create_table(
        "transcript_cues",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("transcript_id", sa.String(36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("start_ms", sa.Integer(), nullable=False),
        sa.Column("end_ms", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("review_status", sa.String(32), nullable=False),
        sa.ForeignKeyConstraint(["transcript_id"], ["transcripts.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("transcript_id", "sequence", name="uq_transcript_cue_sequence"),
    )
    for column in ("transcript_id", "start_ms", "review_status"):
        op.create_index(f"ix_transcript_cues_{column}", "transcript_cues", [column])

    op.create_table(
        "personality_analysis_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("resource_id", sa.String(36), nullable=False),
        sa.Column("transcript_id", sa.String(36), nullable=True),
        sa.Column("engine_version", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["resource_id"], ["research_resources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["transcript_id"], ["transcripts.id"], ondelete="SET NULL"),
    )
    for column in ("resource_id", "transcript_id", "status"):
        op.create_index(f"ix_personality_analysis_runs_{column}", "personality_analysis_runs", [column])

    op.create_table(
        "personality_evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("analysis_run_id", sa.String(36), nullable=False),
        sa.Column("resource_id", sa.String(36), nullable=False),
        sa.Column("transcript_cue_id", sa.String(36), nullable=True),
        sa.Column("dimension_id", sa.String(64), nullable=False),
        sa.Column("dimension_name", sa.String(128), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("locator_type", sa.String(32), nullable=False),
        sa.Column("locator_value", sa.String(255), nullable=False),
        sa.Column("review_status", sa.String(32), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["personality_analysis_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resource_id"], ["research_resources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["transcript_cue_id"], ["transcript_cues.id"], ondelete="SET NULL"),
    )
    for column in ("analysis_run_id", "resource_id", "transcript_cue_id", "dimension_id", "review_status"):
        op.create_index(f"ix_personality_evidence_{column}", "personality_evidence", [column])


def downgrade() -> None:
    for table in (
        "personality_evidence",
        "personality_analysis_runs",
        "transcript_cues",
        "transcripts",
        "video_assets",
        "person_facts",
        "person_external_identities",
        "resource_identifiers",
        "collection_logs",
        "collection_jobs",
        "collection_sources",
    ):
        op.drop_table(table)
