import hashlib
import random
import string
from ringo.model import Base, sqlalchemy as sa
from ringo.model.meta import MetaItem
from ringo.model.base import BaseItem


# NM-Table definitions
nm_user_roles = sa.Table(
    'nm_user_roles', Base.metadata,
    sa.Column('uid', sa.Integer, sa.ForeignKey('users.id')),
    sa.Column('rid', sa.Integer, sa.ForeignKey('roles.id'))
)

nm_usergroup_roles = sa.Table(
    'nm_usergroup_roles', Base.metadata,
    sa.Column('gid', sa.Integer, sa.ForeignKey('usergroups.id')),
    sa.Column('rid', sa.Integer, sa.ForeignKey('roles.id'))
)

nm_user_usergroups = sa.Table(
    'nm_user_usergroups', Base.metadata,
    sa.Column('uid', sa.Integer, sa.ForeignKey('users.id')),
    sa.Column('gid', sa.Integer, sa.ForeignKey('usergroups.id'))
)

nm_role_permissions = sa.Table(
    'nm_role_permissions', Base.metadata,
    sa.Column('rid', sa.Integer, sa.ForeignKey('roles.id')),
    sa.Column('pid', sa.Integer, sa.ForeignKey('permissions.id'))
)


class User(BaseItem, Base):
    __tablename__ = 'users'
    _modul_id = 2
    id = sa.Column(sa.Integer, primary_key=True)
    mid = sa.Column(sa.Integer, sa.ForeignKey('meta.id'))
    login = sa.Column(sa.Text, unique=True, nullable=False)
    password = sa.Column(sa.Text, nullable=False)
    gid = sa.Column(sa.Integer, sa.ForeignKey('usergroups.id'))

    # Relations
    meta = sa.orm.relation("MetaItem", uselist=False,
                           cascade="all, delete-orphan", single_parent=True)
    roles = sa.orm.relationship("Role",
                                secondary=nm_user_roles)
    groups = sa.orm.relationship("Usergroup",
                                 secondary=nm_user_usergroups,
                                 backref='members')
    default_group = sa.orm.relationship("Usergroup", uselist=False)

    # Configuration
    _table_fields = [('login', 'Login'),
                     ('roles', 'Roles'),
                     ('groups', 'Groups')]

    def __unicode__(self):
        return self.login

    def get_roles(self):
        """Returns a list of roles the user has. The list contains
        `Role` object and are collected by loading roles directly
        attached to the user plus roles attached to the groups the user
        is member of

        :returns: List of `Role` instances

        """
        tmp_roles = {}

        # Add roles directly attached to the user.
        for role in self.roles:
            if role.name not in tmp_roles:
                tmp_roles[role.name] = role

        # Add roles directly attached to the user.
        for group in self.groups:
            for role in group.roles:
                if role.name not in tmp_roles:
                    tmp_roles[role.name] = role

        return list(tmp_roles.values())


class Usergroup(BaseItem, Base):
    __tablename__ = 'usergroups'
    _modul_id = 3
    id = sa.Column(sa.Integer, primary_key=True)
    mid = sa.Column(sa.Integer, sa.ForeignKey('meta.id'))
    name = sa.Column(sa.Text, unique=True, nullable=False)

    # Relations
    meta = sa.orm.relation("MetaItem", cascade="all, delete-orphan",
                           single_parent=True)
    roles = sa.orm.relationship("Role", secondary=nm_usergroup_roles)

    # Configuration
    _table_fields = [('name', 'Login'),
                     ('roles', 'Roles')]

    def __unicode__(self):
        return self.name


class Role(BaseItem, Base):
    __tablename__ = 'roles'
    _modul_id = 4
    id = sa.Column(sa.Integer, primary_key=True)
    mid = sa.Column(sa.Integer, sa.ForeignKey('meta.id'))
    name = sa.Column(sa.Text, unique=True, nullable=False)

    # Relations
    meta = sa.orm.relation("MetaItem", cascade="all, delete-orphan",
                           single_parent=True)
    permissions = sa.orm.relationship("Permission",
                                      secondary=nm_role_permissions)

    # Configuration
    _table_fields = [('name', 'Name'),
                     ('permissions', 'Permissions')]

    def __unicode__(self):
        return self.name


class Permission(BaseItem, Base):
    __tablename__ = 'permissions'
    _modul_id = 6
    id = sa.Column(sa.Integer, primary_key=True)
    mid = sa.Column(sa.Integer, sa.ForeignKey('meta.id'))
    name = sa.Column(sa.Text, unique=True, nullable=False)

    meta = sa.orm.relation("MetaItem", cascade="all, delete-orphan",
                           single_parent=True)

    def __unicode__(self):
        return self.name


def init_model(dbsession):
    """Will setup the initial model for the usermanagement. This
    includes creating users, usergroups  roles and permissions.

    :dbsession: Database session to which the items will be added.
    :returns: None

    """
    read_perm = Permission(name='read')
    meta = MetaItem(mid=1, uid=1, gid=None)
    dbsession.add(meta)
    read_perm.meta = meta
    create_perm = Permission(name='create')
    meta = MetaItem(mid=1, uid=1, gid=None)
    dbsession.add(meta)
    create_perm.meta = meta
    update_perm = Permission(name='update')
    meta = MetaItem(mid=1, uid=1, gid=None)
    dbsession.add(meta)
    update_perm.meta = meta
    delete_perm = Permission(name='delete')
    meta = MetaItem(mid=1, uid=1, gid=None)
    dbsession.add(meta)
    delete_perm.meta = meta
    dbsession.add(read_perm)
    dbsession.add(create_perm)
    dbsession.add(update_perm)
    dbsession.add(delete_perm)
    admin_role = Role(name='admin')
    meta = MetaItem(mid=1, uid=1, gid=None)
    dbsession.add(meta)
    admin_role.meta = meta
    admin_role.permissions.append(create_perm)
    admin_role.permissions.append(read_perm)
    admin_role.permissions.append(update_perm)
    admin_role.permissions.append(delete_perm)
    dbsession.add(admin_role)
    role = Role(name='user')
    meta = MetaItem(mid=1, uid=1, gid=None)
    dbsession.add(meta)
    role.meta = meta
    dbsession.add(role)
    admin_usergroup = Usergroup(name='admins')
    admin_usergroup.roles.append(admin_role)
    meta = MetaItem(mid=1, uid=1, gid=None)
    dbsession.add(meta)
    admin_usergroup.meta = meta
    dbsession.add(admin_usergroup)
    usergroup = Usergroup(name='users')
    meta = MetaItem(mid=1, uid=1, gid=None)
    dbsession.add(meta)
    usergroup.meta = meta
    dbsession.add(usergroup)
    pw = hashlib.md5()
    pw.update('secret')
    user = User(login='admin', password=pw.hexdigest())
    user.default_group = admin_usergroup
    user.groups.append(admin_usergroup)
    meta = MetaItem(mid=1, uid=1, gid=None)
    dbsession.add(meta)
    user.meta = meta
    dbsession.add(user)
    #Performance tests
    for i in range(100):
        login = ''.join(random.choice(string.ascii_uppercase
                                      + string.digits) for x in range(8))
        pw.update(login)
        meta = MetaItem(mid=1, uid=1, gid=None)
        dbsession.add(meta)
        user = User(login=login, password=pw.hexdigest())
        user.default_group = admin_usergroup
        user.groups.append(admin_usergroup)
        user.meta = meta
        dbsession.add(user)
