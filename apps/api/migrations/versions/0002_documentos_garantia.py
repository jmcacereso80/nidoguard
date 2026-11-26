"""documentos y garantia del equipo

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('asset_documents',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('asset_id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('filename', sa.String(length=200), nullable=False),
        sa.Column('storage_key', sa.String(length=500), nullable=False),
        sa.Column('content_type', sa.String(length=80), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('sha256', sa.String(length=64), nullable=True),
        sa.Column('uploaded', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['equipment_assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('storage_key'),
    )
    op.create_index('ix_asset_documents_asset_id', 'asset_documents', ['asset_id'])
    op.create_index('ix_asset_documents_organization_id', 'asset_documents', ['organization_id'])
    op.create_index('ix_asset_documents_sha256', 'asset_documents', ['sha256'])
    op.create_table('warranties',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('asset_id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('ends_on', sa.Date(), nullable=False),
        sa.Column('provider', sa.String(length=200), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['equipment_assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['asset_documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('asset_id'),
    )
    op.create_index('ix_warranties_organization_id', 'warranties', ['organization_id'])


def downgrade() -> None:
    op.drop_index('ix_warranties_organization_id', table_name='warranties')
    op.drop_table('warranties')
    op.drop_index('ix_asset_documents_sha256', table_name='asset_documents')
    op.drop_index('ix_asset_documents_organization_id', table_name='asset_documents')
    op.drop_index('ix_asset_documents_asset_id', table_name='asset_documents')
    op.drop_table('asset_documents')
