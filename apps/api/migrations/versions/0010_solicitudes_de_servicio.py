"""solicitudes de servicio, llamadas, cotizaciones, citas y consentimientos

Revision ID: 0010
Revises: 0009
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
PK = dict(server_default=sa.text('gen_random_uuid()'), primary_key=True)
JSON_LIST = dict(server_default=sa.text("'[]'::jsonb"), nullable=False)


def _now():
    return sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        'service_requests', sa.Column('id', UUID, **PK),
        sa.Column('organization_id', UUID, sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('property_id', UUID, sa.ForeignKey('properties.id')),
        sa.Column('asset_id', UUID, sa.ForeignKey('equipment_assets.id', ondelete='SET NULL')),
        sa.Column('care_task_id', UUID, sa.ForeignKey('care_tasks.id', ondelete='SET NULL')),
        sa.Column('created_by', UUID, sa.ForeignKey('users.id')),
        sa.Column('origin', sa.String(10), nullable=False),
        sa.Column('route', sa.String(12), nullable=False, server_default='tecnico'),
        sa.Column('equipment_label', sa.String(200)), sa.Column('symptom', sa.Text()), sa.Column('scope_text', sa.Text()),
        sa.Column('specialty', sa.String(40)),
        sa.Column('urgency', sa.String(12), nullable=False, server_default='semana'),
        sa.Column('safety_alert', sa.String(20)),
        sa.Column('safety_acknowledged', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('status', sa.String(14), nullable=False, server_default='borrador'),
        sa.Column('zone_city', sa.String(120)), sa.Column('zone_colony', sa.String(120)),
        sa.Column('lat', sa.Float()), sa.Column('lng', sa.Float()),
        sa.Column('radius_km', sa.Integer(), nullable=False, server_default='15'),
        sa.Column('target_quotes', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('chosen_quote_id', UUID),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        _now(), sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    for c in ('organization_id', 'asset_id', 'care_task_id', 'status'):
        op.create_index(f'ix_service_requests_{c}', 'service_requests', [c])
    op.create_table(
        'service_calls', sa.Column('id', UUID, **PK),
        sa.Column('request_id', UUID, sa.ForeignKey('service_requests.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider_id', UUID, sa.ForeignKey('service_providers.id')),
        sa.Column('purpose', sa.String(12), nullable=False),
        sa.Column('label', sa.String(20)), sa.Column('distance_km', sa.Float()),
        sa.Column('attempt', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.String(14), nullable=False, server_default='en_cola'),
        sa.Column('scheduled_for', sa.DateTime(timezone=True)),
        sa.Column('retell_call_id', sa.String(80), unique=True),
        sa.Column('duration_s', sa.Integer()), sa.Column('cost_usd', sa.Float()),
        sa.Column('transcript', sa.Text()), sa.Column('recording_key', sa.String(500)), _now(),
    )
    op.create_index('ix_service_calls_request_id', 'service_calls', ['request_id'])
    op.create_table(
        'service_quotes', sa.Column('id', UUID, **PK),
        sa.Column('request_id', UUID, sa.ForeignKey('service_requests.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider_id', UUID, sa.ForeignKey('service_providers.id'), nullable=False),
        sa.Column('call_id', UUID, sa.ForeignKey('service_calls.id')),
        sa.Column('label', sa.String(20), nullable=False),
        sa.Column('rating', sa.Float()), sa.Column('reviews', sa.Integer()), sa.Column('distance_km', sa.Float()),
        sa.Column('scope_quoted', sa.Text()),
        sa.Column('includes', postgresql.JSONB(), **JSON_LIST), sa.Column('excludes', postgresql.JSONB(), **JSON_LIST),
        sa.Column('price_min', sa.Float()), sa.Column('price_max', sa.Float()), sa.Column('price_type', sa.String(30)),
        sa.Column('visit_fee', sa.Float()),
        sa.Column('availability', postgresql.JSONB(), **JSON_LIST),
        sa.Column('warranty_days', sa.Integer()), sa.Column('invoice', sa.Boolean()),
        sa.Column('payment_methods', postgresql.JSONB(), **JSON_LIST),
        sa.Column('matches', sa.String(10)), sa.Column('summary', sa.Text()),
        sa.Column('confidence', postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False), _now(),
    )
    op.create_index('ix_service_quotes_request_id', 'service_quotes', ['request_id'])
    op.create_index('uq_quote_request_provider', 'service_quotes', ['request_id', 'provider_id'], unique=True)
    op.create_table(
        'service_appointments', sa.Column('id', UUID, **PK),
        sa.Column('request_id', UUID, sa.ForeignKey('service_requests.id', ondelete='CASCADE'), nullable=False),
        sa.Column('quote_id', UUID, sa.ForeignKey('service_quotes.id')),
        sa.Column('provider_id', UUID, sa.ForeignKey('service_providers.id')),
        sa.Column('provider_kind', sa.String(10), nullable=False),
        sa.Column('location_type', sa.String(10), nullable=False, server_default='domicilio'),
        sa.Column('center_name', sa.String(200)), sa.Column('center_address', sa.String(300)), sa.Column('folio', sa.String(60)),
        sa.Column('bring', postgresql.JSONB(), **JSON_LIST),
        sa.Column('requested_slot', postgresql.JSONB()),
        sa.Column('starts_at', sa.DateTime(timezone=True)), sa.Column('ends_at', sa.DateTime(timezone=True)),
        sa.Column('status', sa.String(16), nullable=False, server_default='por_confirmar'),
        sa.Column('registered_by_user', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('address_shared_at', sa.DateTime(timezone=True)), sa.Column('final_cost', sa.Float()), _now(),
    )
    op.create_index('ix_service_appointments_request_id', 'service_appointments', ['request_id'])
    op.create_table(
        'consents', sa.Column('id', UUID, **PK),
        sa.Column('user_id', UUID, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('organization_id', UUID, sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('request_id', UUID, sa.ForeignKey('service_requests.id', ondelete='SET NULL')),
        sa.Column('type', sa.String(40), nullable=False), sa.Column('text_version', sa.String(20), nullable=False), _now(),
    )
    op.create_index('ix_consents_user_id', 'consents', ['user_id'])
    op.create_index('ix_consents_organization_id', 'consents', ['organization_id'])


def downgrade() -> None:
    for t in ('consents', 'service_appointments', 'service_quotes', 'service_calls', 'service_requests'):
        op.drop_table(t)
