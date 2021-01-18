import inspect

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

