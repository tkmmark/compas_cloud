import inspect
import importlib

__all__ =   [
            'is_class_method',
            'is_static_method',
            'is_property',
            'is_builtins_instance',
            'is_special_method',
            'get_function',
            'parse_caching_instructions',
            'parse_name',
            'parse_kwargs'
            ]

# ==============================================================================
# CHECK METHODS' TYPES
# ==============================================================================

def is_class_method(cls, name):
    if hasattr(cls, name):
        method = getattr(cls, name)
        return inspect.ismethod(method) and method.__self__ is cls
    else:
        return False


def is_static_method(cls_, name, value=None):
    """Test if a value of a class is static method.

    example::

        class MyClass(object):
            @staticmethod
            def method():
                ...

    :param cls_: the class
    :param name: attribute name
    :param value: attribute value
    """
    if value is None:
        value = getattr(cls_, name)
    assert getattr(cls_, name) == value

    for cls in inspect.getmro(cls_):
        if inspect.isroutine(value):
            if name in cls.__dict__:
                bound_value = cls.__dict__[name]
                if isinstance(bound_value, staticmethod):
                    return True
    return False


def is_property(cls_, name):
    return hasattr(cls_, name) and isinstance(getattr(cls_, name), property)


def is_builtins_instance(data):
    return 'builtin' in data.__class__.__module__


def is_special_method(name, private=True, dunder=True):
    is_dunder = name.startswith('__') and name.endswith('__')
    is_private = name.startswith('_') and not name.startswith('__')
    if private and not dunder:
        return is_private
    elif not private and dunder:
        return is_dunder
    else:
        return is_private or is_dunder

# ==============================================================================
# CHECK INSTANCES' TYPES
# ==============================================================================


# TODO: create a single type checker for all cached ref objs
def is_cached_object_proxy_data(object_):
    if isinstance(object_, dict) and 'cached' in object_ and \
       'protocol' in object_ and object_['protocol'] == 2:
        return True
    else:
        return False

def is_cached_object_proxy(object_):
    from compas_cloud.datastructures.cacheproxy import MetaCachedObjectProxyClass
    if hasattr(object_, '__metaclass__') and object_.__metaclass__ is MetaCachedObjectProxyClass:
        return True
    else:
        return False


# ==============================================================================
# ==============================================================================
# GET FUNCTIONS
# ==============================================================================
# ==============================================================================


def get_function(data):
    # data = data if isinstance(data, dict) else {'package': data}
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
