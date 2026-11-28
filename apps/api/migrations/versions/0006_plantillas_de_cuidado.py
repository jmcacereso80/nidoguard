"""planes de cuidado compartidos por modelo o tipo de equipo

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'care_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('key', sa.String(300), nullable=False, unique=True),
        sa.Column('kind', sa.String(10), nullable=False),
        sa.Column('brand', sa.String(120)),
        sa.Column('model', sa.String(120)),
        sa.Column('category', sa.String(80)),
        sa.Column('items', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('source', sa.String(12), nullable=False, server_default='sugerencia'),
        sa.Column('verified', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('planner', sa.String(80)),
        sa.Column('uses', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('care_templates')
