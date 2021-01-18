from compas_cloud import DUNDERS_NOT_WRAPPED
from compas_cloud.helpers.retrievers import parse_caching_instructions

# ==============================================================================
# CACHED OBJECT PROXY
# ==============================================================================

def proxy_object_name_decorator(text):
    if text.count('\n') == 0:
        text_ = '<< CACHED OBJECT PROXY: ' + text + ' >>'
    else:
        text_ = '<< CACHED OBJECT PROXY:\n' + text + '\n>>'
    return text_


class MetaCachedObjectProxyClass(type):
    _classes = {}

    @staticmethod
    def proxy_getter_factory(name, is_property=True):
        def proxy_getter(self):
            self._assert_server_has_cached()
            # TODO: allow caching of output somehow...
            # cache, dkey, channel = parse_caching_instructions(kwargs)
            cache, dkey, channel = None, None, None
            pass_server = False
            return self._proxy.run_attribute(self._cached, (name, 'getter'),
                                             cache, dkey, channel,
                                             pass_server)
        return proxy_getter

    @staticmethod
    def proxy_setter_factory(name, is_property=True):
        def proxy_setter(self, *args, **kwargs):
            self._assert_server_has_cached()
            cache, dkey, channel = None, None, None
            pass_server = False
            return self._proxy.run_attribute(self._cached, (name, 'setter'),
                                             cache, dkey, channel,
                                             pass_server,
                                             *args, **kwargs)
        return proxy_setter

    @staticmethod
    def proxy_method_factory(name):
        def proxy_method(self, *args, **kwargs):
            self._assert_server_has_cached()
            pass_server = kwargs.pop('pass_server') if 'pass_server' in kwargs else False
            cache, dkey, channel = parse_caching_instructions(kwargs)

            return self._proxy.run_attribute(self._cached, (name, 'method'),
                                             cache, dkey, channel,
                                             pass_server,
                                             *args, **kwargs)
        return proxy_method

    # def set_class_construction_data(cls, proxy, attrs):
    #     cls._proxy = proxy
    #     cls._attrs = attrs

    def build_core_cached_proxy_methods(cls):

        def _run_method(self, name, *args, **kwargs):
            self._assert_server_has_cached()
            pass_server = kwargs.pop('pass_server') if 'pass_server' in kwargs else False
            cache, dkey, channel = parse_caching_instructions(kwargs)
            return self._proxy.run_attribute(self._cached, (name, 'method'),
                                             cache, dkey, channel,
                                             pass_server,
                                             *args, **kwargs)

        def _assert_server_has_cached(self):
            if not self._proxy.has_cached(self._cached):
                raise RuntimeError("Proxy no longer has {}".format(self._cached['cached']))

        def _get(self, as_type=None):
            return self._proxy.get(self._cached, as_type=as_type)

        def _download(self, as_type=None):
            return self._proxy.get(self._cached, as_type=as_type)

        def _destroy(self):
            self._proxy.remove_cached(self._cached)

        def __repr__(self):
            return proxy_object_name_decorator(self._run_method('__repr__', cache=0))

        def __str__(self):
            return proxy_object_name_decorator(self._run_method('__str__', cache=0))

        [setattr(cls, _name, _func) for _name, _func in locals().items() if _name not in ['cls', 'meta']]

    def __new__(meta, name, bases, dict_,
                proxy, attrs, *args, **kwargs):
        """create new object"""

        if name in meta._classes:
            return meta._classes[name]
        else:
            cls_ = super(MetaCachedObjectProxyClass, meta).__new__(meta, name, bases, dict_)
            cls_._proxy = proxy
            cls_._attrs = attrs
            return cls_

    def __init__(cls, name, bases, dct, *args, **kwargs):
        """object proxy instantiation"""

        if name not in MetaCachedObjectProxyClass._classes:
            cls.build_core_cached_proxy_methods()

            for _name, _type in cls._attrs:
                if _type == 'property':
                    _fset = MetaCachedObjectProxyClass.proxy_setter_factory(_name)
                    _fget = property(MetaCachedObjectProxyClass.proxy_getter_factory(_name))
                    setattr(cls, _name, _fget.setter(_fset))
                elif _type == 'method':
                    _mtd = MetaCachedObjectProxyClass.proxy_method_factory(_name)
                    setattr(cls, _name, _mtd)
                elif _type == 'attribute':
                    _fset = MetaCachedObjectProxyClass.proxy_setter_factory(_name)
                    _fget = property(MetaCachedObjectProxyClass.proxy_getter_factory(_name))
                    setattr(cls, _name, _fget.setter(_fset))

            MetaCachedObjectProxyClass._classes[name] = cls

            super(MetaCachedObjectProxyClass, cls).__init__(name, bases, dct)

    def __call__(cls, cached, *args, **kwargs):
        obj =  type.__call__(cls, *args, **kwargs)
        obj._cached = cached
        return obj


def make_cached_object_proxy(proxy, cached_obj_data):
    name                    = proxy_object_name_decorator(cached_obj_data['class_name'])
    cached_ref_obj          = {'cached': cached_obj_data['cached']}

    attrs                   = [(_a, _v) for _a, _v in cached_obj_data['attributes'] if _a not in DUNDERS_NOT_WRAPPED]
    CachedObjectProxyClass  = MetaCachedObjectProxyClass(name, (object,), {'__metaclass__': MetaCachedObjectProxyClass},
                                                         proxy=proxy, attrs=attrs)
    cached_obj_proxy        = CachedObjectProxyClass(cached=cached_ref_obj)

    return cached_obj_proxy
