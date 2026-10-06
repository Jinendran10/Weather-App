"""index locations by latitude and longitude

Revision ID: 0002_locations_lat_lon_index
Revises: 0001_initial_schema
Create Date: 2026-10-06 05:34:18.487939+00:00

"""
from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002_locations_lat_lon_index'
down_revision: Union[str, None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # A database created by the app's create_all() after commit af5bd72 already has this index.
    if not context.is_offline_mode():
        existing = {ix["name"] for ix in sa.inspect(op.get_bind()).get_indexes("locations")}
        if "ix_locations_lat_lon" in existing:
            return
    with op.batch_alter_table('locations', schema=None) as batch_op:
        batch_op.create_index('ix_locations_lat_lon', ['latitude', 'longitude'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('locations', schema=None) as batch_op:
        batch_op.drop_index('ix_locations_lat_lon')

