from types import MethodType

import compas

import compas_cloud as cc
DEFAULT_PORT = cc.CLOUD_DEFAULTS['port']
DEFAULT_HOST = cc.CLOUD_DEFAULTS['host']


def attempt_via_proxy(method_name):
    def outer(method):
        def inner(self, *args, **kwargs):
            try:
                res = method(self, *args, **kwargs)
                # print("No proxy needed for '{}'".format(method_name))
            except (NameError, ImportError):
                # print("Proxy used for '{}'".format(method_name))
                if compas.IPY and cc.has_server(port=self._cloud_port):
                    pself = self.to_cloud(cloud_port=self._cloud_port)
                    res = getattr(pself, method_name)(*args, **kwargs)
                    self.data = pself.data
                    pself._destroy()
                else:
                    res = None
            return res
        return inner
    return outer


class CloudBase(object):

    _UNWRAPPED_METHODS = ['from_cloud', 'to_cloud']
    _ADDED_INIT_KWARGS = ['cloud_instance', 'cloud_autosolve', 'cloud_dkey', 'cloud_protocol', 'cloud_port']

    @staticmethod
    def _auto_cloud_method_factory(method):
        @attempt_via_proxy(method.__name__)
        def wrapped_method(self, *args, **kwargs):
            return method(*args, **kwargs)
        return wrapped_method

    # set wrapped method as an instance method so it will not affect other objects in the run-time instance
    def _wrap_methods_for_cloud_autosolve(self):
        from compas_cloud.helpers.queries import is_static_method
        from compas_cloud.helpers.queries import is_class_method
        # method = filter methods
        mtds_to_wrap = []
        cls_ = self.__class__
        for _mtd_name in dir(self):
            _mtd_is_prop = hasattr(cls_, _mtd_name) and isinstance(getattr(cls_, _mtd_name), property)
            if _mtd_name not in self._UNWRAPPED_METHODS and not _mtd_is_prop:
                _mtd = getattr(self, _mtd_name)
                if callable(_mtd) and not _mtd_name.startswith('_') and \
                   not is_static_method(cls_, _mtd_name) and not is_class_method(cls_, _mtd_name):
                    mtds_to_wrap.append((_mtd_name, _mtd))

        # for each method in methods
        for _mtd_name, _mtd in mtds_to_wrap:
            # rename original method
            setattr(self, "_" + _mtd_name, _mtd)
            # create new method with wrapper decorator
            _wrpd_mtd = self.__class__._auto_cloud_method_factory(_mtd)
            if compas.PY3:
                _wrpd_mtd = MethodType(_wrpd_mtd, self)
            else:
                _wrpd_mtd = MethodType(_wrpd_mtd, self, cls_)
            setattr(self, _mtd_name, _wrpd_mtd)

    def __new__(cls, *args, **kwargs):
        """Instantiation on cloud
        Automatic wrapping..."""

        parse_kwargs = lambda kwargs, name, default: kwargs.pop(name) if name in kwargs else default

        cloud_autosolve = parse_kwargs(kwargs, 'cloud_autosolve', False)
        cloud_instance = parse_kwargs(kwargs, 'cloud_instance', False)
        cloud_dkey = parse_kwargs(kwargs, 'cloud_dkey', None)
        cloud_port = parse_kwargs(kwargs, 'cloud_port', DEFAULT_PORT)
        cloud_channel = parse_kwargs(kwargs, 'cloud_channel', None)
        cloud_protocol = parse_kwargs(kwargs, 'cloud_protocol', 2)

        instc = super(CloudBase, cls).__new__(cls)

        # initialisation manually invoke
        instc.__init__(*args, **kwargs)
        instc._cloud_port = cloud_port

        if not cloud_instance:
            if cloud_autosolve:
                instc._wrap_methods_for_cloud_autosolve()
            return instc
        elif cloud_instance and cc.has_server(port=cloud_port):
            p = cc.get_proxy(port=cloud_port)
            pinstc = p.cache(instc, dkey=cloud_dkey, protocol=cloud_protocol, channel=cloud_channel)
            return pinstc

    def __init__(self, *args, **kwargs):
        super(CloudBase, self).__init__(*args, **kwargs)

    def to_cloud(self, cloud_dkey=None, cache_protocol=2, cloud_port=DEFAULT_PORT, cloud_channel=None):
        if cc.has_server(port=cloud_port):
            p = cc.get_proxy(port=cloud_port)
            pdata = p.cache(self, dkey=cloud_dkey, protocol=cache_protocol, channel=cloud_channel)
            return pdata
        else:
            raise RuntimeError('No server available...')

    @classmethod
    def from_cloud(cls, cached_ref, cloud_port=DEFAULT_PORT, *args, **kwargs):
        if cc.has_server(port=cloud_port):
            p = cc.get_proxy(port=cloud_port, *args, **kwargs)
            retrieved = p.get(cached_ref, *args, **kwargs)
            if not ('as_cache' in kwargs and kwargs['as_cache']):
                retrieved = cls.from_data(retrieved.to_data())
            return retrieved
        else:
            raise RuntimeError('No server available...')




# ==============================================================================
# Main
# ==============================================================================

if __name__ == '__main__':

    pass