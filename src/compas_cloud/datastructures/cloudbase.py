from types import MethodType

import compas

import compas_cloud as cc
CLOUDBASE_ATTRS = cc.CLOUDBASE_ATTRS
DEFAULT_PORT = cc.CLOUD_DEFAULTS['port']
DEFAULT_HOST = cc.CLOUD_DEFAULTS['host']

from compas_cloud.helpers.utils import parse_kwargs
from compas_cloud.helpers.utils import is_static_method, is_class_method, is_property, is_special_method


def attempt_via_proxy(method):
    method_name = method.__name__
    def inner(self, *args, **kwargs):
        try:
            res = method(self, *args, **kwargs)
        except (NameError, ImportError):
            if compas.IPY and cc.has_server(port=self._cloud_port):
                pself = self.to_cloud(cloud_port=self._cloud_port, cloud_dkey=self._cloud_dkey, cloud_channel=self._cloud_channel)
                res = getattr(pself, method_name)(*args, **kwargs)
                self.data = pself.data
                pself._destroy()
            else:
                res = None
        return res
    return inner


class CloudBase(object):

    @staticmethod
    def _auto_cloud_method_factory(method):
        @attempt_via_proxy
        def wrapped_method(self, *args, **kwargs):
            return method(*args, **kwargs)
        return wrapped_method

    # set wrapped method as an instance method so it will not affect other objects in the run-time instance
    def _wrap_methods_for_cloud_autosolve(self):

        attrs_to_wrap = []
        cls_ = self.__class__
        for _attr_name in dir(self):
            if _attr_name not in CLOUDBASE_ATTRS and not is_property(cls_, _attr_name):
                _attr = getattr(self, _attr_name)
                if callable(_attr) and \
                   not is_special_method(_attr_name, private=True, dunder=True) and \
                   not is_static_method(cls_, _attr_name) and \
                   not is_class_method(cls_, _attr_name):
                    attrs_to_wrap.append((_attr_name, _attr))

        # for each method in methods
        for _attr_name, _attr in attrs_to_wrap:
            # rename original method
            setattr(self, "_" + _attr_name, _attr)
            # create new method with wrapper decorator
            _wrpd_attr = self.__class__._auto_cloud_method_factory(_attr)
            if compas.PY3:
                _wrpd_attr = MethodType(_wrpd_attr, self)
            else:
                _wrpd_attr = MethodType(_wrpd_attr, self, cls_)
            setattr(self, _attr_name, _wrpd_attr)

    def __new__(cls, *args, **kwargs):
        """Instantiation on cloud
        Automatic wrapping..."""

        cloud_autosolve = parse_kwargs(kwargs, 'cloud_autosolve', False)
        cloud_instance = parse_kwargs(kwargs, 'cloud_instance', False)
        cloud_dkey = parse_kwargs(kwargs, 'cloud_dkey', None)
        cloud_port = parse_kwargs(kwargs, 'cloud_port', DEFAULT_PORT)
        cloud_channel = parse_kwargs(kwargs, 'cloud_channel', None)
        cloud_protocol = parse_kwargs(kwargs, 'cloud_protocol', 2)

        instc = super(CloudBase, cls).__new__(cls)

        if cloud_instance and cloud_autosolve:
            raise

        if cloud_instance:
            # initialisation manually invoke
            instc.__init__(*args, **kwargs)
            p = cc.get_proxy(port=cloud_port)

            pinstc = p.cache(instc, dkey=cloud_dkey, protocol=cloud_protocol, channel=cloud_channel)
            return pinstc
        else:
            return instc

    def __init__(self, *args, **kwargs):

        cloud_autosolve = parse_kwargs(kwargs, 'cloud_autosolve', False)
        cloud_instance = parse_kwargs(kwargs, 'cloud_instance', False)
        cloud_dkey = parse_kwargs(kwargs, 'cloud_dkey', None)
        cloud_port = parse_kwargs(kwargs, 'cloud_port', DEFAULT_PORT)
        cloud_channel = parse_kwargs(kwargs, 'cloud_channel', None)
        cloud_protocol = parse_kwargs(kwargs, 'cloud_protocol', 2)

        super(CloudBase, self).__init__(*args, **kwargs)

        if cloud_autosolve:
            self._cloud_port = cloud_port
            self._cloud_dkey = cloud_dkey
            self._cloud_channel = cloud_channel
            self._wrap_methods_for_cloud_autosolve()

    def to_cloud(self, cloud_dkey=None, cache_protocol=2, cloud_port=DEFAULT_PORT, cloud_channel=None):
        p = cc.get_proxy(port=cloud_port)
        if p:
            pdata = p.cache(self, dkey=cloud_dkey, protocol=cache_protocol, channel=cloud_channel)
            return pdata
        else:
            raise RuntimeError('No server available...')

    @classmethod
    def from_cloud(cls, cached_ref, cloud_port=DEFAULT_PORT, *args, **kwargs):
        p = cc.get_proxy(port=cloud_port, *args, **kwargs)
        if p:
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