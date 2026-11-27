"""nombre de quien ira a la visita (lo dice el tecnico al confirmar)

Revision ID: 0014
Revises: 0013
"""
from alembic import op
import sqlalchemy as sa

revision = '0014'
down_revision = '0013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('service_appointments', sa.Column('visit_person', sa.String(120)))


def downgrade() -> None:
    op.drop_column('service_appointments', 'visit_person')
