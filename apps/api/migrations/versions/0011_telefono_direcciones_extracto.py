"""telefono de la persona, extracto de la cotizacion y telefono compartido en la cita

Revision ID: 0011
Revises: 0010
"""
from alembic import op
import sqlalchemy as sa

revision = '0011'
down_revision = '0010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('phone_e164', sa.String(20)))
    op.add_column('service_quotes', sa.Column('excerpt', sa.Text()))
    op.add_column('service_appointments', sa.Column('share_phone', sa.Boolean(), server_default=sa.text('false'), nullable=False))


def downgrade() -> None:
    op.drop_column('service_appointments', 'share_phone')
    op.drop_column('service_quotes', 'excerpt')
    op.drop_column('users', 'phone_e164')
