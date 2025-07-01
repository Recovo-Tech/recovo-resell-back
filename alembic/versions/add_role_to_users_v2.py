"""
Add role column to users table

Revision ID: add_role_to_users_v2
Revises: add_second_hand_marketplace
Create Date: 2025-06-30
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "add_role_to_users_v2"
down_revision = "add_second_hand_marketplace"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column(
            "role", sa.String(length=20), nullable=False, server_default="client"
        ),
    )


def downgrade():
    op.drop_column("users", "role")
