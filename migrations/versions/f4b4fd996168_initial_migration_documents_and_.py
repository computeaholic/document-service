"""Initial migration: documents and idempotency_keys tables

Revision ID: f4b4fd996168
Revises: 
Create Date: 2026-02-23 21:13:00.255095

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'f4b4fd996168'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('content', sa.String(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('now()')
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('now()')
        ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create idempotency_keys table
    op.create_table(
        'idempotency_keys',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('key', sa.String(length=128), nullable=False),
        sa.Column('request_hash', sa.String(length=64), nullable=False),
        sa.Column('response_body', sa.Text(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('now()')
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key')
    )
    
    # Create index on idempotency_keys.key for faster lookups
    op.create_index(
        'ix_idempotency_keys_key',
        'idempotency_keys',
        ['key'],
        unique=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_idempotency_keys_key', table_name='idempotency_keys')
    op.drop_table('idempotency_keys')
    op.drop_table('documents')
