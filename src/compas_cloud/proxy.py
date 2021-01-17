from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json
import os

import time
import inspect

from subprocess import Popen
from subprocess import PIPE

import compas


if compas.IPY:
    from .client_net import Client_Net as Client
    import Rhino
else:
    from .client_websockets import Client_Websockets as Client


import compas_cloud as cc
default_port = cc.CLOUD_DEFAULTS['port']
default_host = cc.CLOUD_DEFAULTS['host']

#FIXME
from compas.utilities.encoders import DataDecoder, DataEncoder

from compas_cloud.helpers.errors import ServerSideError
from compas_cloud.helpers.retrievers import parse_caching_instructions
from compas_cloud.helpers.wrappers import retry_if_exception, try_reconnect_to_server
from compas_cloud.helpers.queries import is_cached_object_proxy, is_cached_object_proxy_data
from compas_cloud.datastructures.cacheproxy import make_cached_object_proxy

# ==============================================================================
# ==============================================================================
# PROXY
# ==============================================================================
# ==============================================================================

class Proxy():
    """Proxy is the interface between the user and a websocket client which communicates to websoket server in background.

    Parameters
    ----------
    port : int, optional
        The port number on the remote server.
        Default is ``9000``.

    Notes
    -----

    The service will make the correct (version of the requested) functionality available
    even if that functionality is part of a virtual environment. This is because it
    will use the specific python interpreter for which the functionality is installed to
    start the server.

    If possible, the proxy will try to reconnect to an already existing service

    The proxy will implement corresponding client with either python websokets library or
    .NET depending on environment.

    Examples
    --------

    .. code-block:: python

        from compas_cloud import Proxy
        p = Proxy()
        dr_numpy = p.package('compas.numerical.dr_numpy')

z
    """

    def __init__(self, host=default_host, port=default_port, background=True, errorHandler=None, restart=False):
        """init function that starts a remote server then assigns corresponding client(websockets/.net) to the proxy"""
        self._python = compas._os.select_python(None)
        self.host = host
        self.port = port
        self.background = background
        print(host, port)
        self.client = self.try_reconnect()
        if self.client and restart:
            self.shutdown()
        if not self.client:
            self.client = self.start_server()
        self.callbacks = {}
        self.errorHandler = errorHandler

        # super(Proxy, self).__init__(host=host, port=port,
        #                             background=background, errorHandler=errorHandler)

    def package(self, function, cache=False):
        raise RuntimeError(
            "Proxy.package() has been deprecated, please use Proxy.function() instead.")

    def function(self, function,
                       cache=0, dkey=None, channel=0,
                       pass_server=False):
        """returns wrapper of function that will be executed on server side"""

        if self.errorHandler:
            @self.errorHandler
            @retry_if_exception(Exception, 1, wait=0.5)
            def run_function(*args, **kwargs):
                return self.run_function(function, cache, dkey, channel, pass_server, *args, **kwargs)
            return run_function
        else:
            @retry_if_exception(Exception, 1, wait=0.5)
            def run_function(*args, **kwargs):
                return self.run_function(function, cache, dkey, channel, pass_server, *args, **kwargs)
            return run_function

    # ==============================================================================
    # ==============================================================================
    # PARSERS
    # ==============================================================================
    # ==============================================================================

    def parse_cached_wrappers(self, args, kwargs):

        args = tuple([_arg._cached if is_cached_object_proxy(_arg) else _arg for _arg in args])
        kwargs = {_k: _v._cached if is_cached_object_proxy(_k) else _v for _k, _v in kwargs.items()}

        return args, kwargs

    def parse_callbacks(self, args, kwargs):
        """replace a callback functions with its cached reference then sending it to server"""
        for i, a in enumerate(args):
            cb = a
            if callable(cb):
                args[i] = {'callback': {'id': id(cb)}}
                self.callbacks[id(cb)] = cb
        for key in kwargs:
            cb = kwargs[key]
            if callable(cb):
                kwargs[key] = {'callback': {'id': id(cb)}}
                self.callbacks[id(cb)] = cb
        return args, kwargs

    # ==============================================================================
    # ==============================================================================
    # SEND
    # ==============================================================================
    # ==============================================================================

    @try_reconnect_to_server
    def send(self, data):
        """encode given data before sending to remote server then parse returned result"""

        if not self.client:
            print("There is no connected client, try to restart proxy")
            return

        from pprint import pprint
        istring = json.dumps([data], cls=DataEncoder)

        self.client.send(istring)

        def listen_and_parse():
            result = self.client.receive()
            result = json.loads(result, cls=DataDecoder)[0]  # in order to allow non-iterable outputs
            return result

        result = listen_and_parse()
        # keep receiving response until a non-callback result is returned
        while True:
            if isinstance(result, dict):
                # print(result.keys())
                if 'callback' in result:
                    cb = result['callback']
                    self.callbacks[cb['id']](*cb['args'], **cb['kwargs'])
                    result = listen_and_parse()
                elif 'listen' in result:
                    result = listen_and_parse()
                else:
                    break
            else:
                break

        return result

    def send_only(self, data):
        istring = json.dumps([data], cls=DataEncoder)
        return self.client.send(istring)

    # ==============================================================================
    # ==============================================================================
    # FUNCTIONS & METHODS
    # ==============================================================================
    # ==============================================================================

    # other args: make_copy_first, set_to_temp?
    # on copy?
    def _broadcast_server_error(self, received):
        if isinstance(received, dict) and 'error' in received:
            raise ServerSideError("".join(received['error']))

    def run_function(self, package,
                           _cache=0, _dkey=None, _channel=0,             # default values set when proxy.function() is called initially
                           pass_server=False,
                           *args, **kwargs):
        """pass the arguments to remote function and wait to receive the results"""
        cache, dkey, chnl = parse_caching_instructions(kwargs, _cache, _dkey, _channel)
        args, kwargs = self.parse_callbacks(args, kwargs)
        args, kwargs = self.parse_cached_wrappers(args, kwargs)
        # print(args, kwargs)

        idict = {'request': 'run_function',
                 'package': package,
                 'cache': cache, 'dkey': dkey, 'channel': chnl,          # instructions for caching output: protocol, alias
                 'pass_server': pass_server,
                 'args': args, 'kwargs': kwargs}

        # print('')
        # print(idict)
        result = self.send(idict)
        self._broadcast_server_error(result)

        if is_cached_object_proxy_data(result):
            result = make_cached_object_proxy(proxy=self, cached_obj_data=result)

        return result

    def run_attribute(self, cached_id, _attr,
                      cache=0, dkey=None, channel=0,       # replace can be used to replace
                      pass_server=False,
                      *args, **kwargs):

        args, kwargs = self.parse_callbacks(args, kwargs)
        args, kwargs = self.parse_cached_wrappers(args, kwargs)
        cache = self._process_input_cache_protocol(cache)

        idict = {'request': 'run_method',
                 'get': cached_id,
                 'attr': _attr,
                 'cache': cache, 'dkey': dkey, 'channel': channel,      # instructions for caching output: protocol, alias
                 'pass_server': pass_server,
                 'args': args, 'kwargs': kwargs}

        result = self.send(idict)
        self._broadcast_server_error(result)

        if is_cached_object_proxy_data(result):
            result = make_cached_object_proxy(proxy=self, cached_obj_data=result)

        return result

    def run(self, expression, reset=False):
        idict = {'request': 'run_expression',
                 'expression': expression,
                 'reset': reset}
        result = self.send(idict)
        self._broadcast_server_error(result)
        return result

    # ==============================================================================
    # ==============================================================================
    # OTHERS
    # ==============================================================================
    # ==============================================================================

    def Sessions(self, *args, **kwargs):
        return Sessions_client(self, *args, **kwargs)

    def version(self):
        """get version info of compas cloud server side packages"""
        idict = {'version': True}
        return self.send(idict)

    # ==============================================================================
    # ==============================================================================
    # CACHE MANAGEMENT
    # ==============================================================================
    # ==============================================================================

    def _process_input_cached(self, cached):
        if is_cached_object_proxy(cached):
            cached = cached._cached,
        elif not isinstance(cached, dict):
            cached  = {'cached': cached}
        return cached

    def _process_input_dtype(self, dtype):
        if isinstance(dtype, str):
            dtype = {'dtype_': dtype}
        return dtype

    def _process_input_cache_protocol(self, cache_protocol):
        if cache_protocol is None:
            return 0
        else:
            return int(cache_protocol)

    def set_cache_protocol(self, protocol=2):
        # enforce cache protocol, useful for accessing attributes of cached proxy
        idict = {'request': 'settings'}
        idict.update({'settings': {'cache_protocol': protocol}})
        res = self.send(idict)

        self._broadcast_server_error(res)

        return True

    def cache(self, data, dkey=None, replace=False, protocol=2, channel=0, as_type=None):
        # protocol:
        # -1 means discard
        # 0 means no caching,
        # 1 means basic dict
        # 2 means wrapped object
        as_type = self._process_input_dtype(as_type)
        """cache data or function to remote server and return a reference of it"""
        idict = {'request': 'cache'}
        if callable(data):
            idict.update({'func_to_cache': {
                          'name': data.__name__,
                          'source': inspect.getsource(data)
                          }})
        else:
            idict.update({'to_cache': data,
                          'as_type': as_type,
                          'cache': protocol, 'dkey': dkey, 'channel': channel,
                          'replace': replace})

        cached = self.send(idict)

        if protocol == 2 and not callable(data):
            cached = make_cached_object_proxy(proxy=self, cached_obj_data=cached)

        self._broadcast_server_error(cached)

        return cached

    def cache_from_json(self, file_path, dtype, dkey=None, replace=False, cache=2, channel=0):

        idict = {'request': 'cache_from_json',
                 'file_path': file_path,
                 'dtype_': dtype,
                 'dkey': dkey, 'channel': channel,
                 'cache': cache,
                 'replace': replace}

        result = self.send(idict)
        self._broadcast_server_error(result)

        if is_cached_object_proxy_data(result):
            result = make_cached_object_proxy(proxy=self, cached_obj_data=result)
        return result

    def get_channel_latest(self, channel=None, as_cache=False, as_type=None):

        idict = {'request': 'get_channel_latest',
                 'channel': channel,
                 'as_cache': as_cache,
                 'as_type': as_type}

        res = self.send(idict)

        self._broadcast_server_error(res)

        if as_cache and is_cached_object_proxy_data(res):
            res = make_cached_object_proxy(proxy=self, cached_obj_data=res)
        else:
            res = res['get']

        return res

    def get(self, cached, as_type=None, as_cache=False):

        as_type = self._process_input_dtype(as_type)
        cached = self._process_input_cached(cached)

        idict = {'request': 'get_cached',
                 'get': cached,
                 'as_cache': as_cache,
                 'as_type': as_type}
        res = self.send(idict)

        self._broadcast_server_error(res)

        if as_cache and is_cached_object_proxy_data(res):
            res = make_cached_object_proxy(proxy=self, cached_obj_data=res)
        else:
            res = res['get']

        return res

    def view(self):
        """cache data or function to remote server and return a reference of it"""
        idict = {'request': 'view'}
        return self.send(idict)

    def view_dkeys(self):
        """get content of a cached object stored remotely"""
        idict = {'request': 'view_dkeys'}
        return self.send(idict)

    def get_cached_timestamps(self, cached, channels=None):

        cached = self._process_input_cached(cached)
        idict = {'request': 'get_timestamps',
                 'get': cached, }
        res = self.send(idict)

        return res

    def has_cached(self, cached):
        cached = self._process_input_cached(cached)

        idict = {'request': 'has_cached',
                 'get': cached}
        res = self.send(idict)
        return res

    def remove_cached(self, cached=[], channels=[], all_=False):
        idict = {'request': 'remove_cached'}

        if not all_:
            cached  = [cached] if not isinstance(cached, list) else cached
            to_rmv  = [self._process_input_cached(_to_rmv) for _to_rmv in cached]
            to_rmv  += channels
        else:
            to_rmv  = ['all']

        idict.update({'to_remove': to_rmv})
        self.send(idict)

    # ==============================================================================
    # ==============================================================================
    # SERVER CONNECTION
    # ==============================================================================
    # ==============================================================================

    # Utilities
    # ==============================================================================

    @classmethod
    def has_server(cls, host=default_host, port=default_port):
        """see if there is an existing server"""
        try:
            client = Client(host, port)
        except Exception:
            return False
        return True

    def check(self):
        """check if server connection is good"""
        return self.send({'control': 'check'})

    # Connection
    # ==============================================================================

    def start_server(self):
        """use Popen to start a remote server in background"""
        env = compas._os.prepare_environment()

        args = [self._python, '-m',
                'compas_cloud.server', str(self.port)]

        if self.background:
            print("Starting new cloud server in background at {}:{}".format(
                self.host, self.port))
            self._process = Popen(args, stdout=PIPE, stderr=PIPE, env=env)
        else:
            print("Starting new cloud server with prompt console at {}:{}".format(
                self.host, self.port))
            args[0] = compas._os.select_python('python')
            args = " ".join(args)
            os.system('start ' + args)
        # import sys
        # self._process = Popen(args, stdout=sys.stdout, stderr=sys.stderr, env=env)

        success = False
        count = 20
        while count:
            if compas.IPY:
                Rhino.RhinoApp.Wait()
            try:
                time.sleep(0.2)
                client = Client(self.host, self.port)
            except Exception as e:

                # stop trying if the subprocess is not running anymore
                if self.background:
                    if self._process.poll() is not None:
                        out, err = self._process.communicate()
                        if out:
                            print(out.decode())
                        if err:
                            raise RuntimeError(err.decode())
                        raise RuntimeError(
                            'subprocess terminated, reason unknown')

                count -= 1
                print(e)
                print("\n\n    {} attempts left.".format(count))
            else:
                success = True
                break
        if not success:
            raise RuntimeError("The server is not available.")
        else:
            print("server started with port", self.port)

        return client

    def try_reconnect(self):
        """try to reconnect to a existing server"""
        try:
            client = Client(self.host, self.port)
        except Exception:
            client = None
            return client
        else:
            print("Reconnected to an existing server at {}:{}".format(
                self.host, self.port))
        return client

    def reconnect(self):
        """for clients: try to reconnect to an existing server"""
        self.client = self.try_reconnect()
        if self.client is not None:
            return True
        else:
            return False

    def restart(self):
        """shut down and restart existing server and given ip and port"""
        self.client = self.try_reconnect()
        self.shutdown()
        time.sleep(1)
        self.client = self.start_server()

    def shutdown(self):
        """shut down currently connected server"""
        if self.client:
            if self.send_only({'control': 'shutdown'}):
                self.client = None
                print("server will shutdown and proxy client disconnected.")
        else:
            print("there is already no connected client")


# ==============================================================================
# ==============================================================================
# SESSIONS
# ==============================================================================
# ==============================================================================

class Sessions_client():

    def __init__(self, proxy, *args, **kwargs):
        self.proxy = proxy
        idict = {'sessions': {'command': 'create',
                              'args': args, 'kwargs': kwargs}}
        print(self.proxy.send(idict))

    def start(self):
        idict = {'sessions': {'command': 'start', 'args': (), 'kwargs': {}}}
        print(self.proxy.send(idict))

    def add_task(self, func, *args, **kwargs):
        cached = self.proxy.cache(func)
        idict = {'sessions': {'command': 'add_task',
                              'func': cached, 'args': args, 'kwargs': kwargs}}
        print(self.proxy.send(idict))

    def listen(self):
        idict = {'sessions': {'command': 'listen', 'args': (), 'kwargs': {}}}
        print(self.proxy.send(idict))

    def terminate(self):
        pass


if __name__ == "__main__":
    pass
