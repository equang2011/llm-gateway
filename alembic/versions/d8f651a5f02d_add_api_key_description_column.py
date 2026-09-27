"""add api key description column

Revision ID: d8f651a5f02d
Revises: ca86f91f092a
Create Date: 2026-09-20 23:48:35.176417

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d8f651a5f02d"
down_revision: Union[str, Sequence[str], None] = "ca86f91f092a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table(
        "gateway_api_keys",
        recreate="always",
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "description",
                sa.String(length=255),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "last_used_at",
                sa.DateTime(),
                nullable=True,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table(
        "gateway_api_keys",
        recreate="always",
    ) as batch_op:
        batch_op.drop_column("last_used_at")
        batch_op.drop_column("created_at")
        batch_op.drop_column("description")
