"""agenda con el tecnico (propuestas, recordatorio), cotizaciones descartadas y lineas de servicio de fabricantes

Revision ID: 0012
Revises: 0011
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0012'
down_revision = '0011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('service_appointments', sa.Column('proposal_round', sa.Integer(), server_default=sa.text('0'), nullable=False))
    op.add_column('service_appointments', sa.Column('proposed_slot', postgresql.JSONB()))
    op.add_column('service_appointments', sa.Column('reminder_sent_at', sa.DateTime(timezone=True)))
    op.add_column('service_quotes', sa.Column('declined', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.create_table(
        'manufacturer_service_lines',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('brand_key', sa.String(80), nullable=False, unique=True),
        sa.Column('brand', sa.String(120), nullable=False),
        sa.Column('phone_e164', sa.String(20), nullable=False),
        sa.Column('hours', sa.String(200)),
        sa.Column('channel', sa.String(20), server_default='telefono', nullable=False),
        sa.Column('requires_account_holder', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('data_requested', postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('source', sa.String(300)),
        sa.Column('status', sa.String(14), server_default='por_verificar', nullable=False),
        sa.Column('verified_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('manufacturer_service_lines')
    op.drop_column('service_quotes', 'declined')
    op.drop_column('service_appointments', 'reminder_sent_at')
    op.drop_column('service_appointments', 'proposed_slot')
    op.drop_column('service_appointments', 'proposal_round')
