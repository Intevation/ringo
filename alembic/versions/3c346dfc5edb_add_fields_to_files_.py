"""Add fields to files table

Revision ID: 3c346dfc5edb
Revises: 1403ac1fa61e
Create Date: 2013-08-15 00:48:52.485146

"""

# revision identifiers, used by Alembic.
revision = '3c346dfc5edb'
down_revision = '1403ac1fa61e'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('files', sa.Column('data', sa.LargeBinary(), nullable=True))
    op.add_column('files', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('files', sa.Column('mime', sa.Text(), nullable=True))
    op.add_column('files', sa.Column('name', sa.Text(), nullable=True))
    op.add_column('files', sa.Column('size', sa.Integer(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('files', 'size')
    op.drop_column('files', 'name')
    op.drop_column('files', 'mime')
    op.drop_column('files', 'description')
    op.drop_column('files', 'data')
    ### end Alembic commands ###
