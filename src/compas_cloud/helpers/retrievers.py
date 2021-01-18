
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import importlib

__all__ =   [
            'get_function',
            'parse_caching_instructions',
            'parse_name'
            ]

# ==============================================================================
# ==============================================================================
# GET FUNCTIONS
# ==============================================================================
# ==============================================================================


def get_function(data):
    package = data['package']
    method  = data.get('method', None)

    names   = package.split('.')
    mod     = '.'.join(names[:-1])
    func    = names[-1]
    _func   = names[-1]

    _mod = importlib.import_module(mod)
    _func = getattr(_mod, func)
    if method is not None:
        _func = getattr(_func, method)
    return _func

# ==============================================================================
# ==============================================================================
# CACHING
# ==============================================================================
# ==============================================================================

# TODO: have defaults in settings file...
def parse_caching_instructions(kwargs,
                               _cache=0, _dkey=None, _channel=0):
    cache = _cache
    dkey = _dkey
    channel = _channel
    if 'cache' in kwargs:
        cache = kwargs.pop('cache')
    if 'dkey' in kwargs:
        dkey = kwargs.pop('dkey')
    if 'channel' in kwargs:
        channel = kwargs.pop('channel')

    return cache, dkey, channel


def parse_name(object_):
    if hasattr(object_, 'name'):
        return object_.name
    elif hasattr(object_, '__name__'):
        return object_.__name__
    else:
        return repr(object_)


def parse_kwargs(kwargs, name, default):
    return kwargs.pop(name) if name in kwargs else default
