
from functools import wraps

import compas
import time

if compas.IPY:
    # FIXME: research and use a more specific ConnectionClosedError for the IronPython case
    import Rhino
    from System import AggregateException as ConnectionClosedError
else:
    from websockets.exceptions import ConnectionClosedError


__all__ = ['ServerSideError', 'retry_if_exception', 'reconnect_if_disconnected']


class ServerSideError(Exception):
    pass

def retry_if_exception(ex, max_retries, wait=0):
    def outer(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            assert max_retries > 0
            x = max_retries
            e = RuntimeError("unknown")
            while x:
                if compas.IPY:
                    Rhino.RhinoApp.Wait()
                try:
                    return func(*args, **kwargs)
                except ex as error:
                    e = error
                    print(e)
                    if isinstance(e, ServerSideError):
                        break
                    print('proxy call failed, trying time left:', x)
                    x -= 1
                    time.sleep(wait)
            raise e
        return wrapper
    return outer


def reconnect_if_disconnected(send):
    def _send(self, data):
        x = 2

        while x:
            try:
                return send(self, data)
            except ConnectionClosedError as e:
                print("Unable to connect with server; trying to reconnect now...")
                self.reconnect()
                x -= 1
        raise RuntimeError("unable to connect with server")
    return _send


class dual_class_instance_method(object):
    def __init__(self, method):
        self.method = method

    def __get__(self, obj=None, cls=None):
        @wraps(self.method)
        def _inner(*args, **kwargs):
            if obj is not None:
                return self.method(obj, *args, **kwargs)
            else:
                return self.method(cls, *args, **kwargs)
        return _inner
