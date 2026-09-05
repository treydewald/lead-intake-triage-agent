"""add reviewer name column

Revision ID: 327d880cd1b9
Revises: a95fad549dbf
Create Date: 2026-09-05 01:45:52.460828

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '327d880cd1b9'
down_revision: Union[str, None] = 'a95fad549dbf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('review_queue_item', sa.Column('reviewer_name', sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column('review_queue_item', 'reviewer_name')
