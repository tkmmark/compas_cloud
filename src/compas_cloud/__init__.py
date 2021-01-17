from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import compas

CLOUD_DEFAULTS = {'host': '127.0.0.1', 'port': 9000}

from .helpers import *
from .datastructures import *
from .proxy import Proxy

if not compas.IPY:
    from .sessions import Sessions

__version__ = "0.1.1"


# ==============================================================================
# compas_cloud utilities for convenience...
# ==============================================================================


def has_server(host=CLOUD_DEFAULTS['host'], port=CLOUD_DEFAULTS['port']):
    return Proxy.has_server(host=host, port=port)


def get_proxy(host=CLOUD_DEFAULTS['host'], port=CLOUD_DEFAULTS['port'], **kwargs):
    if has_server(host=host, port=port):
        return Proxy(host=host, port=port, **kwargs)
    return None


__all__ = [name for name in dir() if not name.startswith('_')]
