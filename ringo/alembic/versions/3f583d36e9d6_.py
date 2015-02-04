"""Removed file module

Revision ID: 3f583d36e9d6
Revises: 52b4230d23fe
Create Date: 2015-01-31 23:50:04.352213

"""

# revision identifiers, used by Alembic.
revision = '3f583d36e9d6'
down_revision = '52b4230d23fe'

from alembic import op
import sqlalchemy as sa


UPGRADE = """
DELETE FROM "nm_action_roles" WHERE aid IN (SELECT id FROM actions WHERE mid = 8);
DELETE FROM "actions" WHERE mid = 8;
DELETE FROM "modules" WHERE id = 8;
"""
DOWNGRADE = """"""


def iter_statements(stmts):
    for st in [x for x in stmts.split('\n') if x]:
        op.execute(st)


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('files')
    ### end Alembic commands ###
    iter_statements(UPGRADE)


def downgrade():
    iter_statements(DOWNGRADE)