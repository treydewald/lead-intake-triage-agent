"""add notification delivery columns

Revision ID: a95fad549dbf
Revises: b86e4d4ef367
Create Date: 2026-09-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a95fad549dbf'
down_revision: Union[str, None] = 'b86e4d4ef367'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('notification', sa.Column('external_delivery_status', sa.String(length=16), nullable=True))
    op.add_column('notification', sa.Column('external_delivery_error', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('notification', 'external_delivery_error')
    op.drop_column('notification', 'external_delivery_status')
