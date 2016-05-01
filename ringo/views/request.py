"""Modul to handle requests."""
import logging
import urllib
import urlparse

from formbar.form import Validator
from pyramid.httpexceptions import HTTPFound

from ringo.lib.helpers import import_model, get_action_routename, literal
from ringo.lib.history import History
from ringo.lib.security import (
    has_permission,
    ValueChecker
)
from ringo.lib.sql.cache import invalidate_cache
from ringo.views.helpers import (
    get_item_from_request,
    get_item_modul
)

log = logging.getLogger(__name__)

invalid_form_message = "The information contained errors. "
"<strong>All entries (including error-free) were not "
"saved!</strong> Please correct your entries in the "
"fields marked in red and resave."


def form_has_errors(field, data, context):
    """Simple validation callback which returns True if the form has not
    errors an validation. Please make sure that this validators gets
    called as last validator of all validators get the final result of
    the validation."""
    # context is the current formbar form.
    return not context.has_errors()


def encode_unicode_dict(unicodedict, encoding="utf-8"):
    bytedict = {}
    for key in unicodedict:
        if isinstance(unicodedict[key], unicode):
            bytedict[key] = unicodedict[key].encode(encoding)
        elif isinstance(unicodedict[key], dict):
            bytedict[key] = encode_unicode_dict(unicodedict[key])
        else:
            bytedict[key] = unicodedict[key]
    return bytedict


def decode_bytestring_dict(bytedict, encoding="utf-8"):
    unicodedict = {}
    for key in bytedict:
        if isinstance(bytedict[key], str):
            unicodedict[key] = bytedict[key].decode(encoding)
        elif isinstance(bytedict[key], dict):
            unicodedict[key] = decode_bytestring_dict(bytedict[key])
        else:
            unicodedict[key] = bytedict[key]
    return unicodedict


def encode_values(values):
    """Returns a string with encode the values in the given dictionary.

    :values: dictionary with key values pairs
    :returns: String key1:value1,key2:value2...

    """
    # Because urlencode can not handle unicode strings we encode the
    # whole dictionary into utf8 bytestrings first.
    return urllib.urlencode(encode_unicode_dict(values))


def decode_values(encoded):
    """Returns a dictionay with decoded values in the string. See
    encode_values function.

    :encoded : String key1:value1,key2:value2...
    :returns: Dictionary with key values pairs
    """
    # We convert the encoded querystring into a bystring to enforce that
    # parse_pq returns a dictionary which can be later decoded using
    # decode_bystring_dict. If we use the encoded string directly the
    # returned dicionary would contain bytestring as unicode. e.g
    # u'M\xc3\xbcller' which can't be decoded later.
    encoded = str(encoded)

    # Now convert the query string into a dictionary with UTF-8 encoded
    # bytestring values.
    values = urlparse.parse_qs(encoded)
    for key in values:
        values[key] = values[key][0]
    # Finally convert this dictionary back into a unicode dictionary
    return decode_bytestring_dict(values)


def is_confirmed(request):
    """Returns True id the request is confirmed"""
    return request.params.get('confirmed') == "1"


def handle_event(request, item, event):
    """Will call the event listeners for the given event on every base
    class of the given item."""
    for class_ in item.__class__.__bases__:
        if hasattr(class_, event + '_handler'):
            handler = getattr(class_, event + '_handler')
            handler(request, item)


def handle_callback(request, callback, item=None):
    """Will call the given callback

    :request: Current request
    :callback: Callable function or list of callable functions
    :item: item for which the callback will be called.
    :returns: item

    """
    if not item:
        item = get_item_from_request(request)
    if isinstance(callback, list):
        for cb in callback:
            item = cb(request, item)
    elif callback:
        item = callback(request, item)
    return item


def handle_add_relation(request, item):
    """Handle linking of the new item to antoher relation. The relation
    was provided as GET parameter in the current request and is now
    saved in the session.

    :request: Current request
    :item: new item with should be linked

    """
    clazz = request.context.__model__
    addrelation = request.session.get('%s.addrelation' % clazz)
    if not addrelation:
        return item
    rrel, rclazz, rid = addrelation.split(':')
    parent = import_model(rclazz)
    pfactory = parent.get_item_factory()
    pitem = pfactory.load(rid, db=request.db)
    log.debug('Linking %s to %s in %s' % (item, pitem, rrel))
    tmpattr = getattr(pitem, rrel)
    tmpattr.append(item)
    # Delete value from session after the relation has been added
    del request.session['%s.addrelation' % clazz]
    request.session.save()


def handle_caching(request):
    """Will handle invalidation of the cache

    :request: TODO

    """
    # Invalidate cache
    invalidate_cache()
    clazz = request.context.__model__
    if request.session.get('%s.form' % clazz):
        del request.session['%s.form' % clazz]
    request.session.save()


def handle_POST_request(form, request, callback, event, renderers=None):
    """

    :form: loaded formbar form
    :request: actual request
    :callback: callbacks
    :renderers: renderers
    :event: Name of the event (update, create...) Used for the event handler
    :returns: True or False

    """

    if "blobforms" in request.params:
        return False

    _ = request.translate
    clazz = request.context.__model__
    item_label = get_item_modul(request, clazz).get_label()
    item = get_item_from_request(request)
    translation_params = {
        'item_type': item_label,
        'item': item
    }

    validator = create_validator(_(invalid_form_message), form)
    form.add_validator(validator)

    if not form.validate(request.params):
        msg = _(generate_validation_errormessage(event),
                mapping=translation_params)
        log.debug(msg)
        request.session.flash(msg, 'error')
        return False

    try:
        permission_checker = ValueChecker()
        if event == "create":
            permission_checker.check(clazz, form.data, request)
            item = create_new_item(clazz, form, request)
            request.context.item = item
            values = {}
        else:
            values = permission_checker.check(clazz, form.data, request, item)
        item.save(values, request)
        handle_event(request, item, event)
        handle_add_relation(request, item)
        handle_callback(request, callback)
        handle_caching(request)
        msg, log_msg = generate_successmessage(event,
                                               item, item_label, request.user)
        log.info(log_msg)
        success_message = _(msg, mapping=translation_params)
        request.session.flash(success_message, 'success')

    except Exception as error:
        translation_params['error'] = unicode(error.message)
        msg = _(generate_save_errormessage(event), mapping=translation_params)
        log.exception(msg)
        request.session.flash(msg, 'error')
        return False
    else:
        return True


def create_new_item(clazz, form, request):
    item_factory = get_item_factory(clazz, request)
    item = item_factory.create(request.user, form.data)
    return item


def get_item_factory(clazz, request):
    try:
        factory = clazz.get_item_factory(request)
    except TypeError:
        # Old version of get_item_factory method which does
        # not take an request parameter.
        factory = clazz.get_item_factory()
        factory._request = request
    return factory


def generate_successmessage(event, item, item_label, user):
    msg = 'Edited ${item_type} "${item}" successfully.'
    log_msg = u'User {user.login} edited {item_label} {item.id}' \
        .format(item_label=item_label, item=item, user=user)
    if event == "create":
        msg = 'Created new ${item_type} successfully.'
        log_msg = u'User {user.login} created {item_label} {item.id}' \
            .format(item_label=item_label, item=item, user=user)
    return (msg, log_msg)


def generate_save_errormessage(event):
    suffix = '${item_type} "${item}": ${error}.'
    if event == "create":
        suffix = 'new ${item_type}: ${error}.'
    return 'Error while saving ' + suffix


def generate_validation_errormessage(event):
    suffix = '${item_type} "${item}".'
    if event == 'create':
        suffix = 'new ${item_type}.'
    return 'Error on validation' + suffix


def create_validator(error_message, form):
    # Add a *special* validator to the form to trigger rendering a
    # permanent info pane at the top of the form in case of errors on
    # validation. This info has been added because users reported data
    # loss because of formbar/ringo default behaviour of not saving
    # anything in case of errors. Users seems to expect that the valid
    # part of the data has been saved. This info should make the user
    # aware of the fact that nothing has been saved in case of errors.
    return Validator(None, literal(error_message),
                     callback=form_has_errors, context=form)


def handle_redirect_on_success(request):
    """Will return a redirect. If there has been a saved "backurl" the
    redirect will on on this url. In all other cases the function will
    try to determine if the item in the request can be opened in edit
    mode or not. If the current user is allowed to open the item in
    edit mode then the update view is called. Else the read view is
    called.

    :request: Current request
    :returns: Redirect
    """

    item = get_item_from_request(request)
    clazz = request.context.__model__
    backurl = request.session.get('%s.backurl' % clazz)
    if backurl:
        # Redirect to the configured backurl.
        del request.session['%s.backurl' % clazz]
        request.session.save()
        return HTTPFound(location=backurl)
    else:
        # Handle redirect after success.
        # Check if the user is allowed to call the url after saving
        if has_permission("update", item, request):
            route_name = get_action_routename(item, 'update')
            url = request.route_path(route_name, id=item.id)
        else:
            route_name = get_action_routename(item, 'read')
            url = request.route_path(route_name, id=item.id)
        return HTTPFound(location=url)


def handle_history(request):
    history = request.session.get('history')
    if history is None:
        history = History([])
    history.push(request.url)
    request.session['history'] = history


def handle_params(request):
    """Handles varios sytem GET params comming with the request
    Known params are:

     * backurl: A url which should be called instead of the default
       action after the next request succeeds. The backurl will be saved
       in the session and stays there until it is deleted on a
       successfull request. So take care to delete it to not mess up
       with the application logic.
     * form: The name of a alternative form configuration which is
       used for the request.
     * values: A comma separated list of key/value pair. Key and value
       are separated with an ":"
     * addrelation: A ":" separated string 'relation:class:id' to identify that
       a item with id should be linked to the relation of this item.
    """
    clazz = request.context.__model__
    params = {}
    backurl = request.GET.get('backurl')
    if backurl:
        request.session['%s.backurl' % clazz] = backurl
        params['backurl'] = backurl
    values = request.GET.get('values')
    if values:
        params['values'] = {}
        values = decode_values(values)
        for key in values:
            params['values'][key] = values[key]
    form = request.GET.get('form')
    if form:
        # request.session['%s.form' % clazz] = form
        params['form'] = form
    relation = request.GET.get('addrelation')
    if relation:
        request.session['%s.addrelation' % clazz] = relation
        params['addrelation'] = relation
    request.session.save()
    return params


def get_return_value(request):
    """Will return a dictionary of values used as context in the
    templates. The dictionary will include:

    * clazz: clazz of the current request
    * item: item of the current request

    :request: Current request
    :returns: Dictionary with values as context
    """
    rvalues = {}
    clazz = request.context.__model__
    item = get_item_from_request(request)
    rvalues['clazz'] = clazz
    rvalues['item'] = item
    return rvalues
