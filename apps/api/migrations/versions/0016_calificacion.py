"""calificacion de la atencion (1 a 5 estrellas)

Revision ID: 0016
Revises: 0015
"""
from alembic import op
import sqlalchemy as sa

revision = '0016'
down_revision = '0015'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('service_appointments', sa.Column('service_rating', sa.SmallInteger()))
    op.add_column('service_appointments', sa.Column('rating_comment', sa.String(300)))
    op.add_column('service_appointments', sa.Column('rated_at', sa.DateTime(timezone=True)))
    op.create_check_constraint('ck_service_rating_1_5', 'service_appointments', 'service_rating IS NULL OR service_rating BETWEEN 1 AND 5')


def downgrade() -> None:
    op.drop_constraint('ck_service_rating_1_5', 'service_appointments', type_='check')
    op.drop_column('service_appointments', 'rated_at')
    op.drop_column('service_appointments', 'rating_comment')
    op.drop_column('service_appointments', 'service_rating')
