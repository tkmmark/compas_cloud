import importlib

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