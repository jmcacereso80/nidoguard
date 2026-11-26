"""base de conocimiento por modelo: manuales

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('model_knowledge',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('model_key', sa.String(length=200), nullable=False),
        sa.Column('brand', sa.String(length=120), nullable=False),
        sa.Column('model', sa.String(length=120), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=True),
        sa.Column('source_url', sa.String(length=800), nullable=True),
        sa.Column('storage_key', sa.String(length=500), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('next_try_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('model_key'),
    )
    op.create_table('model_research_runs',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('model_key', sa.String(length=200), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_model_research_runs_model_key', 'model_research_runs', ['model_key'])


def downgrade() -> None:
    op.drop_index('ix_model_research_runs_model_key', table_name='model_research_runs')
    op.drop_table('model_research_runs')
    op.drop_table('model_knowledge')
