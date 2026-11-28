"""directorio compartido de tecnicos y sus busquedas

Revision ID: 0008
Revises: 0007
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'service_providers',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('source', sa.String(20), nullable=False),
        sa.Column('source_id', sa.String(200), nullable=False, unique=True),
        sa.Column('name', sa.String(300), nullable=False),
        sa.Column('phone_e164', sa.String(20)),
        sa.Column('website', sa.String(500)),
        sa.Column('address', sa.String(500)),
        sa.Column('city', sa.String(120)),
        sa.Column('colony', sa.String(120)),
        sa.Column('lat', sa.Float()),
        sa.Column('lng', sa.Float()),
        sa.Column('specialties', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('brands', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('rating', sa.Float()),
        sa.Column('reviews', sa.Integer()),
        sa.Column('hours', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('status', sa.String(20), nullable=False, server_default='activo'),
        sa.Column('do_not_call', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('answered', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('quotes_given', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_called_at', sa.DateTime(timezone=True)),
        sa.Column('scraped_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_service_providers_phone_e164', 'service_providers', ['phone_e164'])
    op.create_index('ix_service_providers_city', 'service_providers', ['city'])
    op.create_table(
        'provider_searches',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('key', sa.String(200), nullable=False, unique=True),
        sa.Column('city', sa.String(120), nullable=False),
        sa.Column('specialty', sa.String(60), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('results', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('new_providers', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('detail', sa.Text()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('provider_searches')
    op.drop_index('ix_service_providers_city', table_name='service_providers')
    op.drop_index('ix_service_providers_phone_e164', table_name='service_providers')
    op.drop_table('service_providers')
