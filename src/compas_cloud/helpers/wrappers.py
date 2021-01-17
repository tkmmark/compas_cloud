
from functools import wraps

import compas
import time

if compas.IPY:
    # FIXME: research and use a more specific ConnectionClosedError for the IronPython case
    import Rhino
    from System import AggregateException as ConnectionClosedError
else:
    from websockets.exceptions import ConnectionClosedError

from compas_cloud.helpers.errors import ServerSideError

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


def try_reconnect_to_server(send):
    def _send(self, data):
        x = 2
        # return send(self, data)
        while x:
            try:
                return send(self, data)
            except ConnectionClosedError as e:
                ("Unable to connect with server; trying to reconnect now...")
                self.reconnect()
                x -= 1
        raise RuntimeError("unable to connect with server")
    return _send
