"""nota de acceso para la visita

Revision ID: 0015
Revises: 0014
"""
from alembic import op
import sqlalchemy as sa

revision = '0015'
down_revision = '0014'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('service_appointments', sa.Column('access_notes', sa.String(300)))


def downgrade() -> None:
    op.drop_column('service_appointments', 'access_notes')
