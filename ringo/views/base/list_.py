import uuid
import logging
from sqlalchemy import or_
from ringo.model.base import BaseFactory, get_item_list
from ringo.model.user import User
from ringo.lib.alchemy import is_relation
from ringo.lib.table import get_table_config
from ringo.lib.helpers.misc import get_item_modul
from ringo.lib.helpers import literal
from ringo.lib.security import has_permission
from ringo.lib.renderer import (
    ListRenderer,
    DTListRenderer
)
from ringo.lib.renderer.dialogs import (
    WarningDialogRenderer
)
from ringo.views.response import JSONResponse

# The dictionary will hold the request handlers for bundled actions. The
# dictionary will be filled from the view definitions
_bundle_request_handlers = {}

log = logging.getLogger(__name__)


def get_bundle_action_handler(mapping, action, module):
    if module in mapping:
        views = mapping[module]
        if action in views:
            return views[action]
    return mapping["default"].get(action)


def set_bundle_action_handler(key, handler, module="default"):
    if module in _bundle_request_handlers:
        mod_actions = _bundle_request_handlers.get(module)
    else:
        _bundle_request_handlers[module] = {}
        mod_actions = _bundle_request_handlers.get(module)
    mod_actions[key] = handler
    _bundle_request_handlers[module] = mod_actions


def handle_paginating(clazz, request):
    """Returns a tupe of current page and pagesize. The default page and
    size is page on and all items on one page. This is also the default
    if pagination is not enabled for the table."""

    name = clazz.__tablename__
    # Default pagination options
    table_config = get_table_config(clazz)
    settings = request.registry.settings
    default = settings.get("layout.advanced_overviews") == "true"
    # Only set paginated if the table is the advancedsearch as the
    # simple search provides its own client sided pagination.
    if table_config.is_paginated() and table_config.is_advancedsearch(default):
        default_page = 0  # First page
        default_size = 50
    else:
        return (0, None)

    # Get pagination from session
    page = request.session.get('%s.list.pagination_page' % name, default_page)
    size = request.session.get('%s.list.pagination_size' % name, default_size)

    # Overwrite options with options from get request
    page = int(request.GET.get('pagination_page', page))
    size = request.GET.get('pagination_size', size)
    if size:
        size = int(size)
    else:
        size = None

    if 'reset' in request.params:
        request.session['%s.list.pagination_page' % name] = default_page
        request.session['%s.list.pagination_size' % name] = default_size
    else:
        request.session['%s.list.pagination_page' % name] = page
        request.session['%s.list.pagination_size' % name] = size
    request.session.save()

    return (page, size)


def handle_sorting(clazz, request):
    """Return a tuple of *fieldname* and *sortorder* (asc, desc). The
    sorting is determined in the follwoing order: First try to get the
    sorting from the current request (GET-Param). If there are no
    sorting params try to get the params saved in the session or if
    requested from a saved search. As last
    fallback use the default sorting for the table.
    """
    name = clazz.__tablename__

    # Default sorting options
    default_field = get_table_config(clazz).get_default_sort_column()
    default_order = get_table_config(clazz).get_default_sort_order()

    # Get sorting from the session. If there is no saved sorting use the
    # default value.
    field = request.session.get('%s.list.sort_field' % name, default_field)
    order = request.session.get('%s.list.sort_order' % name, default_order)

    # Get saved sorting from the the saved search.
    saved_search_id = request.params.get('saved')
    if saved_search_id:
        searches_dic = request.user.settings.get('searches', {})
        if searches_dic:
            search = searches_dic.get(name)
            if search:
                field, order = search.get(saved_search_id, [[], [], None])[1]

    # Get sorting from the request. If there is no sorting option in
    # the request then use the saved sorting options.
    field = request.GET.get('sort_field', field)
    order = request.GET.get('sort_order', order)

    # Save current sorting in the session
    if 'reset' in request.params:
        request.session['%s.list.sort_field' % name] = default_field
        request.session['%s.list.sort_order' % name] = default_order
    else:
        request.session['%s.list.sort_field' % name] = field
        request.session['%s.list.sort_order' % name] = order
    request.session.save()

    return field, order


def get_search(clazz, request):
    """Returns a list of tuples with the search word and the fieldname.
    The function will first look if there is already a saved search in
    the session for the overview of the given clazz. If there is no
    previous search the start with an empty search stack.  The following
    behavior differs depending if it is a POST or GET request:

    1. GET
    Return either an empty search stack or return the saved stack in the
    session.

    2. POST
    Get the new submitted search. If the search is not already on the
    stack, then push it.  If the search word is empty, then pop the last
    search from the stack.  Finally return the modified stack.

    Please note the this function will not save the modified search
    stack in the session! This should be done elsewhere. E.g Depending
    if the search was successfull.
    """
    name = clazz.__tablename__
    # Default search fielter
    default_search = get_table_config(clazz).get_default_search()
    # Check if there is already a saved search in the session, If not
    # use the default search.
    saved_search = (request.session.get('%s.list.search' % name, []) or
                    default_search)

    regexpr = request.session.get('%s.list.search.regexpr' % name, False)
    if "enableregexpr" in request.params:
        request.session['%s.list.search.regexpr' % name] = True
        return saved_search
    elif "disableregexpr" in request.params:
        request.session['%s.list.search.regexpr' % name] = False
        return saved_search

    if 'reset' in request.params:
        saved_search = []

    # If the request is not a equest from the search form then
    # abort here and return the saved search params if there are any.
    form_name = request.params.get('form')
    if form_name != "search":
        return saved_search

    saved_search_id = request.params.get('saved')
    if saved_search_id:
        searches_dic = request.user.settings.get('searches', {})
        if searches_dic:
            searches_dic_search = searches_dic.get(name)
            if searches_dic_search:
                return searches_dic_search.get(saved_search_id, [[],
                                               [], None])[0]
    elif "save" in request.params:
        return saved_search
    elif "delete" in request.params:
        return saved_search
    else:
        search = request.params.get('search')
        search_field = request.params.get('field')

    # If search is empty try to pop the last filter in the saved search
    if search == "" and len(saved_search) > 0:
        popped = saved_search.pop()
        log.debug('Popping %s from search stack' % repr(popped))

    # Iterate over the saved search. If the search is not already in the
    # stack push it.
    if search != "":
        found = False
        for x in saved_search:
            if search == x[0] and search_field == x[1]:
                found = True
                break
        if not found:
            log.debug('Adding search for "%s" in field "%s"' % (search,
                                                                search_field))
            if search:
                saved_search.append((search, search_field, regexpr))
    return saved_search


def _query_add_permission_filter(query, request, clazz):
    modul = get_item_modul(request, clazz)
    is_admin = False
    is_allowed = True
    for role in request.user.roles:
        if role.name == "admin":
            is_admin = True
            break
        for permission in role.permissions:
            if permission.mid != modul.id or permission.name.lower() != "read":
                continue
            elif permission.admin or role.admin:
                is_admin = True
                break
            else:
                is_allowed = True
    if is_admin:
        # User is allowd to read all items
        return query
    elif is_allowed:
        # User is not allowd to read items based on the uid and groups
        usergroups = [g.id for g in request.user.groups]
        query = query.filter(or_(clazz.uid == request.user.id, clazz.gid.in_(usergroups)))
        return query
    else:
        # User is not allowd to read anything
        return None


def load_items(request, clazz, list_params):
    """
    Return a list of items which can be used as input for the
    get_item_list methods. The purpose of this method is to handle as
    much as possible regarding sorting/searching/pagination on the DB to
    reduce the load in the application.


    :request: Current request
    :clazz: Class of items to load
    :list_params: Dictionary with params for optimzed loading of the the
    items. Those params are used to build specific SQL Queries which
    already include aspects like sorting, filtering and pagination to
    reduce the load in the application. If not provided all filtering
    etc must be done later in the application. See related methods of
    the :class:BaseList.
    loaded.
    :returns: List of class:BaseItem objects.
    """

    if list_params["search"]:
        # Search is currently not supported in optimized loading. So
        # return None and do the work on application side using the
        # Baselist methods.
        return None, 0

    #################################
    #  Filter query on permissions  #
    #################################
    query = request.db.query(clazz)
    query = _query_add_permission_filter(query, request, clazz)
    if query is None:
        return [], 0

    ############################
    #  Sorting and paginating  #
    ############################
    if list_params["sorting"]:
        try:
            sort_column = getattr(clazz, list_params["sorting"][0])
        except AttributeError:
            return None, 0

        # Sorting is only supported on a few attributes.
        if isinstance(sort_column, property):
            return None, 0
        if is_relation(clazz, list_params["sorting"][0]):
            return None, 0

        sort_order = list_params["sorting"][1]
        if sort_order == "asc":
            query = query.order_by(sort_column)
        else:
            query = query.order_by(sort_column.desc())

    total = query.count()
    if list_params["pagination"] and list_params["pagination"][1]:
        start = list_params["pagination"][0] * list_params["pagination"][1]
        end = start + list_params["pagination"][1]
        items = query.slice(start, end)
    else:
        items = query.all()

    # Items must be a list otherwise we get TypeError: object of type
    # 'CachingQuery' has no len() later.
    items = [item for item in items]
    return items, total


def bundle_(request):
    clazz = request.context.__model__
    module = get_item_modul(request, clazz)
    _ = request.translate

    # Handle bundle params. If the request has the bundle_action param
    # the request is the intial request for a bundled action. In this
    # case we can delete all previous selected and stored item ids in
    # the session.
    params = request.params.mixed()
    if params.get('bundle_action'):
        request.session['%s.bundle.action' % clazz] = params.get('bundle_action')
        try:
            del request.session['%s.bundle.items' % clazz]
        except KeyError:
            pass
        request.session['%s.bundle.items' % clazz] = params.get('id', [])
    bundle_action = request.session.get('%s.bundle.action' % clazz)
    ids = request.session.get('%s.bundle.items' % clazz)

    # Check if the user selected at least one item. If not show an
    # dialog informing that the selection is empty.
    if not ids:
        title = _("Empty selection")
        body = _("You have not selected any item in the list. "
                 "Click 'OK' to return to the overview.")
        renderer = WarningDialogRenderer(request, title, body)
        rvalue = {}
        rvalue['dialog'] = literal(renderer.render(url=request.referrer))
        return rvalue

    # If the user only selects one single item it is not a list. So
    # convert it to a list with one item.
    if not isinstance(ids, list):
        ids = [ids]

    factory = clazz.get_item_factory()
    items = []
    ignored_items = []
    for id in ids:
        # Check if the user is allowed to call the requested action on
        # the loaded item. If so append it the the bundle, if not ignore
        # it.
        item = factory.load(id)
        if has_permission(bundle_action.lower(), item, request):
            items.append(item)
        else:
            ignored_items.append(item)

    # After checking the permissions the list of items might be empty.
    # If so show a warning to the user to inform him that the selected
    # action is not applicable.
    if not items:
        title = _("${action} not applicable",
                  mapping={"action": bundle_action})
        body = _("After checking the permissions no items remain "
                 "for which an '${action}' can be performed. "
                 "(${num} items were filtered out.)",
                 mapping={"action": bundle_action,
                          "num": len(ignored_items)})
        renderer = WarningDialogRenderer(request, title, body)
        rvalue = {}
        rvalue['dialog'] = literal(renderer.render(url=request.referrer))
        return rvalue

    handler = get_bundle_action_handler(_bundle_request_handlers,
                                        bundle_action.lower(),
                                        module.name)
    return handler(request, items, None)


def get_list_renderer(listing, request, table=None):
    """Returns the renderer for an listing.
    Allow to use DTListRenderer if the renderer configuration is set."""
    tableconfig = get_table_config(listing.clazz, table)
    settings = request.registry.settings
    default = settings.get("layout.advanced_overviews") == "true"
    if tableconfig.is_advancedsearch(default):
        return ListRenderer(listing, table)
    else:
        return DTListRenderer(listing, table)


def get_base_list(clazz, request, user, table):
    """Helper function in views to get a BaseList instance for the
    given clazz. In contrast to the known "get_item_list" function
    which function will also handle searching, sorting and pagination
    based on the parameter privided within the current request.

    This function makes the search, pagination and sorting feature (as
    used in the advanced search) available in other external views.

    :clazz: Class of item which will be loaded.
    :request: Current request.
    :user: Current user. If None, than all items of a class will be loaded.
    :table: Name of the table configuration which is used for the listing.
    :returns: BaseList instance
    """
    # If the user enters the overview page of an item we assume that the
    # user actually leaves any context where a former set backurl is
    # relevant anymore. So delete it.
    backurl = request.session.get('%s.backurl' % clazz)
    if backurl:
        # Redirect to the configured backurl.
        del request.session['%s.backurl' % clazz]
        request.session.save()

    search = get_search(clazz, request)
    sorting = handle_sorting(clazz, request)
    pagination_page, pagination_size = handle_paginating(clazz, request)

    list_params = {}
    list_params["search"] = search
    list_params["sorting"] = sorting
    list_params["pagination"] = (pagination_page, pagination_size)

    # Try to do an optimized loading of items. If the loading succeeds
    # the loaded items will be used to build an item list. If for some
    # reasone the loading was'nt successfull items will be None and
    # loading etc will be done completely in application.
    if request.ringo.feature.dev_optimized_list_load:
        items, total = load_items(request, clazz, list_params)
        listing = get_item_list(request, clazz, user=user, items=items)
        # Ok no items are loaded. We will need to do sorting and filtering
        # on out own.
        if items is None:
            listing.sort(sorting[0], sorting[1])
            listing.filter(search, request, table)
    else:
        listing = get_item_list(request, clazz, user=user)
        listing.sort(sorting[0], sorting[1])
        listing.filter(search, request, table)

    total = len(listing.items)
    listing.paginate(total, pagination_page, pagination_size)

    # Only save the search if there are items
    if len(listing.items) > 0:
        request.session['%s.list.search' % clazz.__tablename__] = search
        if (request.params.get('form') == "search"):
            if "save" in request.params:
                query_name = request.params.get('save')
                user = BaseFactory(User).load(request.user.id)
                searches_dic = user.settings.get('searches', {})
                searches_dic_search = searches_dic.get(clazz.__tablename__, {})

                # Check if there is already a search saved with the name
                found = False
                for xxx in searches_dic_search.values():
                    if xxx[1] == query_name:
                        found = True
                        break
                if not found:
                    searches_dic_search[str(uuid.uuid1())] = (search, sorting, query_name)
                searches_dic[clazz.__tablename__] = searches_dic_search
                user.settings.set('searches', searches_dic)
                request.db.flush()
            elif "delete" in request.params:
                query_key = request.params.get('delete')
                user = BaseFactory(User).load(request.user.id)
                searches_dic = user.settings.get('searches', {})
                searches_dic_search = searches_dic.get(clazz.__tablename__, {})
                try:
                    del searches_dic_search[query_key]
                except:
                    pass
                searches_dic[clazz.__tablename__] = searches_dic_search
                user.settings.set('searches', searches_dic)
                request.db.flush()
        request.session.save()
    return listing


def list_(request):
    clazz = request.context.__model__
    listing = get_base_list(clazz, request, request.user, "overview")
    renderer = get_list_renderer(listing, request, request.params.get("table"))
    rendered_page = renderer.render(request)
    rvalue = {}
    rvalue['clazz'] = clazz
    rvalue['listing'] = rendered_page
    rvalue['itemlist'] = listing
    return rvalue


def rest_list(request):
    """Returns a JSON objcet with all item of a clazz. The list does not
    have any capabilities for sorting or filtering

    :request: Current request.
    :returns: JSON object.

    """
    clazz = request.context.__model__
    listing = get_item_list(request, clazz, user=request.user)
    return JSONResponse(True, listing)
