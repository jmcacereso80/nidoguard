"""Mi casa: nombres y apellidos de la persona y direccion principal

Revision ID: 0013
Revises: 0012
"""
from alembic import op
import sqlalchemy as sa

revision = '0013'
down_revision = '0012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('first_name', sa.String(120)))
    op.add_column('users', sa.Column('last_name', sa.String(160)))
    op.add_column('properties', sa.Column('is_primary', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    # lo que ya habia: el nombre completo se parte en nombres (primera palabra) y apellidos (el resto)
    op.execute("UPDATE users SET first_name = split_part(trim(name), ' ', 1), "
               "last_name = NULLIF(trim(substr(trim(name), length(split_part(trim(name), ' ', 1)) + 1)), '') "
               "WHERE name IS NOT NULL AND trim(name) <> ''")
    # la primera direccion de cada hogar queda como principal
    op.execute("UPDATE properties SET is_primary = true WHERE id IN "
               "(SELECT DISTINCT ON (organization_id) id FROM properties ORDER BY organization_id, created_at)")


def downgrade() -> None:
    op.drop_column('properties', 'is_primary')
    op.drop_column('users', 'last_name')
    op.drop_column('users', 'first_name')
