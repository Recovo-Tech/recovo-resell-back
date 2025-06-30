"""
Change user id to UUID

Revision ID: user_id_to_uuid
Revises: add_role_to_users_v2
Create Date: 2025-06-30
"""

from alembic import op
import sqlalchemy as sa
import uuid
from sqlalchemy.dialects import postgresql

revision = 'user_id_to_uuid'
down_revision = 'add_role_to_users_v2'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Drop foreign key constraints
    op.drop_constraint('carts_user_id_fkey', 'carts', type_='foreignkey')
    op.drop_constraint('second_hand_products_seller_id_fkey', 'second_hand_products', type_='foreignkey')
    # 2. Add new nullable UUID column to users
    op.add_column('users', sa.Column('id_new', postgresql.UUID(as_uuid=True), nullable=True))
    # 3. Create mapping from old id to new uuid
    conn = op.get_bind()
    users = conn.execute(sa.text('SELECT id FROM users')).fetchall()
    id_map = {}
    for user in users:
        new_uuid = str(uuid.uuid4())
        id_map[user[0]] = new_uuid
        conn.execute(sa.text('UPDATE users SET id_new = :uuid WHERE id = :id'), {'uuid': new_uuid, 'id': user[0]})
    # 4. Add new nullable UUID columns to referencing tables
    op.add_column('carts', sa.Column('user_id_new', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('second_hand_products', sa.Column('seller_id_new', postgresql.UUID(as_uuid=True), nullable=True))
    # 5. Update referencing tables with new UUIDs
    carts = conn.execute(sa.text('SELECT id, user_id FROM carts')).fetchall()
    for cart in carts:
        if cart[1] in id_map:
            conn.execute(sa.text('UPDATE carts SET user_id_new = :uuid WHERE id = :id'), {'uuid': id_map[cart[1]], 'id': cart[0]})
    shp = conn.execute(sa.text('SELECT id, seller_id FROM second_hand_products')).fetchall()
    for product in shp:
        if product[1] in id_map:
            conn.execute(sa.text('UPDATE second_hand_products SET seller_id_new = :uuid WHERE id = :id'), {'uuid': id_map[product[1]], 'id': product[0]})
    # 6. Set new columns as non-nullable
    op.alter_column('carts', 'user_id_new', nullable=False)
    op.alter_column('second_hand_products', 'seller_id_new', nullable=False)
    # 7. Drop old PK constraint and columns
    op.drop_constraint('users_pkey', 'users', type_='primary')
    op.drop_column('users', 'id')
    op.alter_column('users', 'id_new', new_column_name='id')
    op.create_primary_key('users_pkey', 'users', ['id'])
    # 8. Drop old foreign key columns
    op.drop_column('carts', 'user_id')
    op.drop_column('second_hand_products', 'seller_id')
    # 9. Rename new columns
    op.alter_column('carts', 'user_id_new', new_column_name='user_id')
    op.alter_column('second_hand_products', 'seller_id_new', new_column_name='seller_id')
    # 10. Re-create foreign key constraints
    op.create_foreign_key('carts_user_id_fkey', 'carts', 'users', ['user_id'], ['id'])
    op.create_foreign_key('second_hand_products_seller_id_fkey', 'second_hand_products', 'users', ['seller_id'], ['id'])


def downgrade():
    op.drop_constraint('carts_user_id_fkey', 'carts', type_='foreignkey')
    op.drop_constraint('second_hand_products_seller_id_fkey', 'second_hand_products', type_='foreignkey')
    op.drop_constraint('users_pkey', 'users', type_='primary')
    op.add_column('users', sa.Column('id_old', sa.Integer(), nullable=False))
    op.drop_column('users', 'id')
    op.alter_column('users', 'id_old', new_column_name='id')
    op.create_primary_key('users_pkey', 'users', ['id'])
    op.create_foreign_key('carts_user_id_fkey', 'carts', 'users', ['user_id'], ['id'])
    op.create_foreign_key('second_hand_products_seller_id_fkey', 'second_hand_products', 'users', ['seller_id'], ['id'])
