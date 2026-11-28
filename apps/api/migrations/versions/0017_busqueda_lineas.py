"""busqueda automatica de la linea de servicio de cada marca

Revision ID: 0017
Revises: 0016
"""
from alembic import op
import sqlalchemy as sa

revision = '0017'
down_revision = '0016'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('manufacturer_service_lines', 'phone_e164', existing_type=sa.String(20), nullable=True)
    op.add_column('manufacturer_service_lines', sa.Column('found_by', sa.String(10)))
    op.add_column('manufacturer_service_lines', sa.Column('found_at', sa.DateTime(timezone=True)))
    op.add_column('manufacturer_service_lines', sa.Column('confirmed_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('manufacturer_service_lines', sa.Column('wrong_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('service_requests', sa.Column('line_feedback', sa.Boolean()))


def downgrade() -> None:
    op.drop_column('service_requests', 'line_feedback')
    op.drop_column('manufacturer_service_lines', 'wrong_count')
    op.drop_column('manufacturer_service_lines', 'confirmed_count')
    op.drop_column('manufacturer_service_lines', 'found_at')
    op.drop_column('manufacturer_service_lines', 'found_by')
    op.execute("DELETE FROM manufacturer_service_lines WHERE phone_e164 IS NULL")
    op.alter_column('manufacturer_service_lines', 'phone_e164', existing_type=sa.String(20), nullable=False)
