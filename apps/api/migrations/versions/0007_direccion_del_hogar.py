"""direccion del hogar con coordenadas

Revision ID: 0007
Revises: 0006
"""
from alembic import op
import sqlalchemy as sa

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('properties', sa.Column('street', sa.String(200)))
    op.add_column('properties', sa.Column('colony', sa.String(120)))
    op.add_column('properties', sa.Column('postal_code', sa.String(10)))
    op.add_column('properties', sa.Column('city', sa.String(120)))
    op.add_column('properties', sa.Column('state', sa.String(120)))
    op.add_column('properties', sa.Column('lat', sa.Float()))
    op.add_column('properties', sa.Column('lng', sa.Float()))
    op.add_column('properties', sa.Column('search_radius_km', sa.Integer(), nullable=False, server_default='15'))
    op.add_column('properties', sa.Column('geocoded_at', sa.DateTime(timezone=True)))


def downgrade() -> None:
    for c in ('geocoded_at', 'search_radius_km', 'lng', 'lat', 'state', 'city', 'postal_code', 'colony', 'street'):
        op.drop_column('properties', c)
