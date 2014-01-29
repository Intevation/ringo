import os
import logging
import pkg_resources
from beaker.cache import cache_regions
from pyramid.config import Configurator
from pyramid.events import BeforeRender, NewRequest
from pyramid_beaker import session_factory_from_settings

from sqlalchemy import engine_from_config

log = logging.getLogger(__name__)


from ringo.resources import (
    get_resource_factory,
)
from ringo.lib.sql import (
    DBSession,
)
from ringo.model import (
    Base,
)
from ringo.model.base import (
    clear_cache,
)
from ringo.model.user import (
    User,
    Profile,
    Usergroup,
    Role
)
from ringo.model.modul import (
    ModulItem,
    ActionItem,
)
from ringo.model.appointment import (
    Appointment
)
from ringo.lib import (
    helpers,
    security
)
from ringo.lib.i18n import (
    locale_negotiator,
)

# DO NOT REMOVE THESE LINES
# BEGIN AUTOGENERATED IMPORTS
from ringo.model.file import File
from ringo.model.news import News
from ringo.model.log import Log
from ringo.model.comment import Comment
from ringo.model.tag import Tag
from ringo.model.todo import Todo
from ringo.model.form import Form
# AUTOREPLACEIMPORT
# END AUTOGENERATED IMPORTS

base_dir = pkg_resources.get_distribution("ringo").location
template_dir = os.path.join(base_dir, 'ringo', 'templates')

# Directory with templates to generate views and models
modul_template_dir = os.path.join(base_dir, 'ringo', 'scripts', 'templates')


def add_renderer_globals(event):
    request = event['request']
    event['h'] = helpers
    event['s'] = security
    event['_'] = request.translate
    event['N_'] = request.translate
    event['localizer'] = request.localizer


def connect_on_request(event):
    request = event.request
    request.db = DBSession
    request.add_finished_callback(close_db_connection)
    # Try to clear the cache on every request
    clear_cache()


def close_db_connection(request):
    request.db.close()

def add_rest_service(config, clazz):
    """Set routes for basic RESTfull service on CRUD operations on the item

    :config: Pylons config instance
    :clazz: The clazz of the module for which the new routes will be set up.
    :returns: config

    """
    # load modul to get the enabled actions
    factory = ModulItem.get_item_factory()
    modul = factory.load(clazz._modul_id)
    name = clazz.__tablename__
    for action in [action for action in modul.actions
                   if action.name.lower() in
                   ['list', 'create', 'read', 'update', 'delete']]:
        route_name = "rest-%s-%s" % (name, action.name.lower())

        url = action.url.split("/")
        if len(url) > 1:
            route_url = "rest/%s/%s" % (name, url[1])
        else:
            route_url = "rest/%s" % (name)
        #route_url = "rest/%s/%s" % (name, action.url)
        log.debug("Adding route: %s, %s" % (route_name, route_url))
        config.add_route(route_name, route_url,
                         factory=get_resource_factory(clazz, modul))
    return config

def add_route(config, clazz):
    """Setup routes for the activates actions of the given modul.
    Therefor the modul will be loaded to get the configured actions. The
    new routes will be added with the following name and url:

    * Name: $modulname-$actionname
    * Url:  $modulname/$actionurl

    Note, that the actionname can be configured only as admin.

    Further a clazz specific factory will be added to the route which is
    later used to setup the ACL of items of the modul.

    :config: Pylons config instance
    :clazz: The clazz of the module for which the new routes will be set up.
    :returns: config

    """
    # load modul to get the enabled actions
    factory = ModulItem.get_item_factory()
    modul = factory.load(clazz._modul_id)
    name = clazz.__tablename__
    for action in modul.actions:
        route_name = "%s-%s" % (name, action.name.lower())
        route_url = "%s/%s" % (name, action.url)
        log.debug("Adding route: %s, %s" % (route_name, route_url))
        config.add_route(route_name, route_url,
                         factory=get_resource_factory(clazz, modul))
    return add_rest_service(config, clazz)


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    config = Configurator(settings=settings,
                          locale_negotiator=locale_negotiator)

    # configure cache regions
    cache_regions.update({
        'short_term':{
            'expire':'60',
            'type':'memory'
        }
    })

    config.set_session_factory(session_factory_from_settings(settings))
    config.include('ringo')
    return config.make_wsgi_app()

def includeme(config):
    log.info('Setup of Ringo...')
    config = setup_pyramid_modules(config)
    log.info('-> Modules finished.')
    config = setup_subscribers(config)
    log.info('-> Subscribers finished.')
    config = setup_security(config)
    log.info('-> Security finished.')
    config = setup_static_views(config)
    log.info('-> Static views finished.')
    config = setup_routes(config)
    log.info('-> Routes finished.')
    config = setup_translation(config)
    log.info('-> Translation finished.')
    config.scan()
    log.info('OK :) Setup of Ringo finished.')

def setup_pyramid_modules(config):
    config.include('pyramid_handlers')
    config.include('pyramid_beaker')
    return config

def setup_security(config):
    config.include('ringo.lib.security.setup_ringo_security')
    return config

def setup_translation(config):
    config.add_translation_dirs('ringo:locale/')
    return config

def setup_subscribers(config):
    config.add_subscriber(connect_on_request, NewRequest)
    config.add_subscriber(add_renderer_globals, BeforeRender)
    return config

def setup_static_views(config):
    config.add_static_view('static',
                           path='ringo:static',
                           cache_max_age=3600)
    config.add_static_view('images',
                           path='ringo:static/images',
                           cache_max_age=3600)
    config.add_static_view('bootstrap',
                           path='ringo:static/bootstrap',
                           cache_max_age=3600)
    config.add_static_view('css',
                           path='ringo:static/css',
                           cache_max_age=3600)
    return config

def setup_routes(config):
    """Function which will setup the routes of the ringo application"""

    # Helpers
    #########
    config.add_route('set_current_form_page', 'set_current_form_page')

    # SINGLE PAGES
    ##############
    config.add_route('login', 'auth/login')
    config.add_route('register_user', 'auth/register_user')
    config.add_route('confirm_user', 'auth/confirm_user/{token}')
    config.add_route('forgot_password', 'auth/forgot_password')
    config.add_route('reset_password', 'auth/reset_password/{token}')
    config.add_route('logout', 'auth/logout')
    config.add_route('version', 'version')
    config.add_route('contact', 'contact')
    config.add_route('about', 'about')
    config.add_route('home', '/')

    # MODULES
    #########
    # Modules
    add_route(config, ModulItem)
    add_route(config, ActionItem)
    # Users
    add_route(config, User)
    config.add_route('users-changepassword',
                     'users/changepassword/{id}',
                     factory=get_resource_factory(User))
    # Usergroups
    add_route(config, Usergroup)
    # Roles
    add_route(config, Role)
    # Profile
    add_route(config, Profile)
    # Appointments
    add_route(config, Appointment)

    # DO NOT REMOVE THESE LINES
    # BEGIN AUTOGENERATED ROUTES
    add_route(config, File)
    add_route(config, News)
    add_route(config, Log)
    add_route(config, Comment)
    add_route(config, Tag)
    add_route(config, Todo)
    add_route(config, Form)
    # AUTOREPLACEROUTE
    # END AUTOGENERATED ROUTES

    return config
