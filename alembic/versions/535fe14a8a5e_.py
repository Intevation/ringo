"""Added tags module

Revision ID: 535fe14a8a5e
Revises: 2ad27e728587
Create Date: 2014-01-02 18:11:13.767901

"""

# revision identifiers, used by Alembic.
revision = '535fe14a8a5e'
down_revision = '2ad27e728587'

from alembic import op
import sqlalchemy as sa


INSERTS = """
INSERT INTO "modules" VALUES(12,'tags','ringo.model.tag.Tag','Tag','Tags',NULL,NULL,'admin-menu');
INSERT INTO "actions" VALUES(53,12,'List','list','icon-list-alt',NULL);
INSERT INTO "actions" VALUES(54,12,'Create','create',' icon-plus',NULL);
INSERT INTO "actions" VALUES(55,12,'Read','read/{id}','icon-eye-open',NULL);
INSERT INTO "actions" VALUES(56,12,'Update','update/{id}','icon-edit',NULL);
INSERT INTO "actions" VALUES(57,12,'Delete','delete/{id}','icon-trash',NULL);
"""
DELETES = """
DELETE FROM "actions" WHERE id = 53;
DELETE FROM "actions" WHERE id = 54;
DELETE FROM "actions" WHERE id = 55;
DELETE FROM "actions" WHERE id = 56;
DELETE FROM "actions" WHERE id = 57;
DELETE FROM "modules" WHERE id = 11;
"""


def iter_statements(stmts):
    for st in stmts.split('\n'):
        op.execute(st)


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('tags',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('gid', sa.Integer(), nullable=True),
    sa.Column('uid', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['gid'], ['usergroups.id'], ),
    sa.ForeignKeyConstraint(['uid'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    ### end Alembic commands ###
    iter_statements(INSERTS)


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('tags')
    ### end Alembic commands ###
    iter_statements(DELETES)