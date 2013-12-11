"""empty message

Revision ID: 5a7b9035d52
Revises: 32154d55ffe7
Create Date: 2013-12-11 13:51:58.714097

"""

# revision identifiers, used by Alembic.
revision = '5a7b9035d52'
down_revision = '32154d55ffe7'

from alembic import op
import sqlalchemy as sa


INSERTS = """"""
DELETES = """"""


def iter_statements(stmts):
    for st in stmts.split('\n'):
        op.execute(st)


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('forms', sa.Column('review_state_id', sa.Integer(), nullable=True))
    ### end Alembic commands ###
    iter_statements(INSERTS)


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('forms', 'review_state_id')
    ### end Alembic commands ###
    iter_statements(DELETES)
