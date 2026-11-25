"""Add versioned practice knowledge, extraction runs and case concepts."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import LONGTEXT

revision = "20261125_05"
down_revision = "20261030_04"
branch_labels = None
depends_on = None


def large_text():
    return sa.Text().with_variant(LONGTEXT(), "mysql", "mariadb")


def upgrade():
    op.create_table(
        "practice_cases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("resource_id", sa.String(36), sa.ForeignKey("research_resources.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("creation_key", sa.String(64), nullable=False, unique=True),
        sa.Column("source_json", large_text(), nullable=False),
        sa.Column("draft_revision", sa.Integer(), nullable=False),
        sa.Column("published_revision", sa.Integer()),
        sa.Column("withdrawn_through", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_practice_cases_resource_id", "practice_cases", ["resource_id"])
    op.create_table(
        "practice_case_revisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("practice_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("content_json", large_text(), nullable=False),
        sa.Column("submitted_at", sa.DateTime()),
        sa.Column("published_at", sa.DateTime()),
        sa.Column("reviewer", sa.String(100), nullable=False),
        sa.Column("review_note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("case_id", "revision", name="uq_practice_case_revision"),
    )
    op.create_table(
        "practice_evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("revision_id", sa.String(36), sa.ForeignKey("practice_case_revisions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field_name", sa.String(24), nullable=False),
        sa.Column("segment_id", sa.String(36), nullable=False),
        sa.Column("start_char", sa.Integer(), nullable=False),
        sa.Column("end_char", sa.Integer(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
    )
    op.create_index("ix_practice_evidence_revision_id", "practice_evidence", ["revision_id"])
    op.create_table(
        "practice_extraction_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("resource_id", sa.String(36), sa.ForeignKey("research_resources.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False, unique=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("input_json", large_text(), nullable=False),
        sa.Column("config_json", sa.Text(), nullable=False),
        sa.Column("result_json", large_text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("finished_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_practice_extraction_runs_resource_id", "practice_extraction_runs", ["resource_id"])
    op.create_table(
        "practice_concepts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("normalized_label", sa.String(256), nullable=False),
        sa.Column("aliases_json", sa.Text(), nullable=False),
        sa.UniqueConstraint("kind", "normalized_label", name="uq_practice_concept_label"),
    )
    op.create_table(
        "practice_case_concepts",
        sa.Column("revision_id", sa.String(36), sa.ForeignKey("practice_case_revisions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("concept_id", sa.String(36), sa.ForeignKey("practice_concepts.id", ondelete="RESTRICT"), primary_key=True),
    )
    op.create_index("ix_practice_case_concepts_concept_id", "practice_case_concepts", ["concept_id"])


def downgrade():
    op.drop_table("practice_case_concepts")
    op.drop_table("practice_concepts")
    op.drop_table("practice_extraction_runs")
    op.drop_table("practice_evidence")
    op.drop_table("practice_case_revisions")
    op.drop_table("practice_cases")
