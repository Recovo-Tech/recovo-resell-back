"""add_name_and_surname_to_user

Revision ID: f3bad83f1f27
Revises: 001_unified_migration
Create Date: 2025-07-02 11:33:50.357123

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f3bad83f1f27"
down_revision: Union[str, None] = "001_unified_migration"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###

    op.add_column("users", sa.Column("name", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("surname", sa.String(length=100), nullable=True))

    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("users", "surname")
    op.drop_column("users", "name")
    # ### end Alembic commands ###
