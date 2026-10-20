"""add knowledge retrieval and evaluation runs

Revision ID: 20261020_03
Revises: 20261019_02
Create Date: 2026-10-20
"""

from alembic import op
import sqlalchemy as sa


revision = "20261020_03"
down_revision = "20261019_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_query_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("query", sa.String(500), nullable=False),
        sa.Column("filters_json", sa.Text(), nullable=False),
        sa.Column("top_k", sa.Integer(), nullable=False),
        sa.Column("results_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_knowledge_query_runs_query", "knowledge_query_runs", ["query"])
    op.create_table(
        "retrieval_evaluation_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("dataset_json", sa.Text(), nullable=False),
        sa.Column("metrics_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("retrieval_evaluation_runs")
    op.drop_table("knowledge_query_runs")
