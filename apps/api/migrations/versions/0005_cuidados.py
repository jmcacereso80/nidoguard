"""cuidados recurrentes por equipo

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'care_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('equipment_assets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('detail', sa.String(300)),
        sa.Column('instructions', sa.Text()),
        sa.Column('every_n', sa.Integer(), nullable=False),
        sa.Column('every_unit', sa.String(10), nullable=False),
        sa.Column('priority', sa.String(10), nullable=False, server_default='media'),
        sa.Column('source', sa.String(12), nullable=False, server_default='sugerencia'),
        sa.Column('status', sa.String(12), nullable=False, server_default='sugerida'),
        sa.Column('next_due', sa.Date(), nullable=False),
        sa.Column('last_done_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_care_tasks_asset_id', 'care_tasks', ['asset_id'])
    op.create_index('ix_care_tasks_organization_id', 'care_tasks', ['organization_id'])
    op.create_index('ix_care_tasks_next_due', 'care_tasks', ['next_due'])
    op.create_table(
        'care_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('care_tasks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('equipment_assets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('done_on', sa.Date(), nullable=False),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_care_records_task_id', 'care_records', ['task_id'])
    op.create_index('ix_care_records_asset_id', 'care_records', ['asset_id'])
    op.create_index('ix_care_records_organization_id', 'care_records', ['organization_id'])


def downgrade() -> None:
    op.drop_table('care_records')
    op.drop_table('care_tasks')
