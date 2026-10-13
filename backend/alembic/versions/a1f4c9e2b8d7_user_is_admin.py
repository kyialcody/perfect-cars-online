"""user_account.is_admin flag (SQLAdmin access, issue #18)

Revision ID: a1f4c9e2b8d7
Revises: 2a390eb73cb9
Create Date: 2026-06-17 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1f4c9e2b8d7"
down_revision: Union[str, None] = "2a390eb73cb9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_account",
        sa.Column(
            "is_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("user_account", "is_admin")
