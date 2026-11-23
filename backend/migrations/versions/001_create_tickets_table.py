"""Create tickets table.

Revision ID: 001_create_tickets_table
Revises: 
Create Date: 2026-11-23 13:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_create_tickets_table"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tickets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="open"),
        sa.Column("predicted_category", sa.String(length=100), nullable=False),
        sa.Column("category_confidence", sa.Float(), nullable=False),
        sa.Column("predicted_priority", sa.String(length=50), nullable=False),
        sa.Column("priority_confidence", sa.Float(), nullable=False),
        sa.Column("corrected_category", sa.String(length=100), nullable=True),
        sa.Column("category_probabilities", sa.JSON(), nullable=True),
        sa.Column("priority_probabilities", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tickets_status", "tickets", ["status"])
    op.create_index("ix_tickets_predicted_category", "tickets", ["predicted_category"])
    op.create_index("ix_tickets_predicted_priority", "tickets", ["predicted_priority"])
    op.create_index("ix_tickets_status_priority", "tickets", ["status", "predicted_priority"])
    op.create_index("ix_tickets_created_at", "tickets", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_tickets_created_at", table_name="tickets")
    op.drop_index("ix_tickets_status_priority", table_name="tickets")
    op.drop_index("ix_tickets_predicted_priority", table_name="tickets")
    op.drop_index("ix_tickets_predicted_category", table_name="tickets")
    op.drop_index("ix_tickets_status", table_name="tickets")
    op.drop_table("tickets")
