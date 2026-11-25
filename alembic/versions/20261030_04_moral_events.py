"""Add versioned Rest event evidence; preserve existing research data."""
from alembic import op
import sqlalchemy as sa
revision = '20261030_04'
down_revision = '20261020_03'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('moral_events',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('resource_id',sa.String(36),sa.ForeignKey('research_resources.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('fingerprint',sa.String(64),unique=True,nullable=False),
        sa.Column('snapshot_json',sa.Text(),nullable=False),
        sa.Column('eligibility',sa.String(24),nullable=False),
        sa.Column('review_revision',sa.Integer(),nullable=False),
        sa.Column('created_at',sa.DateTime(),nullable=False))
    op.create_index('ix_moral_events_resource_id','moral_events',['resource_id'])
    op.create_table('moral_runs',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('event_id',sa.String(36),sa.ForeignKey('moral_events.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('method',sa.String(32),nullable=False),
        sa.Column('status',sa.String(32),nullable=False),
        sa.Column('config_json',sa.Text(),nullable=False),
        sa.Column('result_json',sa.Text(),nullable=False),
        sa.Column('raw_output',sa.Text(),nullable=False),
        sa.Column('error',sa.Text(),nullable=False),
        sa.Column('created_at',sa.DateTime(),nullable=False))
    op.create_index('ix_moral_runs_event_id','moral_runs',['event_id'])
    op.create_table('moral_reviews',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('event_id',sa.String(36),sa.ForeignKey('moral_events.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('revision',sa.Integer(),nullable=False),
        sa.Column('reviewer',sa.String(100),nullable=False),
        sa.Column('eligibility',sa.String(24),nullable=False),
        sa.Column('codes_json',sa.Text(),nullable=False),
        sa.Column('note',sa.Text(),nullable=False),
        sa.Column('created_at',sa.DateTime(),nullable=False))
    op.create_index('ix_moral_reviews_event_id','moral_reviews',['event_id'])

def downgrade():
    op.drop_table('moral_reviews')
    op.drop_table('moral_runs')
    op.drop_table('moral_events')
