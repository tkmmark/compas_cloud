from autobahn.asyncio.websocket import WebSocketServerProtocol

try:
    import importlib
    import json
    from threading import Thread
    from multiprocessing import Queue
    import time
    import sys
    import traceback
    import pkg_resources
    from types import SimpleNamespace

    # from compas_struct_ml.server import CompasServerProtocol
except ImportError:
    pass

from copy import deepcopy
from collections import OrderedDict

import compas
from compas.utilities import timestamp

import compas_cloud as cc
from compas_cloud.helpers.encoders import cls_from_dtype, DataDecoder, DataEncoder
from compas_cloud.helpers.utils import get_function, parse_name
from compas_cloud.helpers.utils import is_class_method, is_static_method, is_builtins_instance

from compas_cloud.sessions import Sessions


class CompasServerProtocol(WebSocketServerProtocol):
    """The CompasServerProtocol defines the behaviour of compas cloud server"""

    # ==============================================================================
    # DEFAULTS
    # ==============================================================================

    default_logs = {
                        'cached':   {
                                    'id_to_channel': {},
                                    'id_to_dkey': {},
                                    'dkey_to_id': {},
                                    },
                        'requests': {},
                        'times':    {
                                    'created': {'by_channel': {},
                                                'by_id': {},
                                                'by_dkey': {}},
                                    'accessed': {'by_channel': {},
                                                'by_id': {},
                                                'by_dkey': {}},
                                    }
                        }
    default_settings = {'cache_protocol': None, 'save_requests': False}

    # ==============================================================================
    # ==============================================================================
    # OPERATION DATA
    # ==============================================================================
    # ==============================================================================

    cached = {}
    settings = deepcopy(default_settings)
    logs = deepcopy(default_logs)
    sandbox = {}
    sessions = None

    # ==============================================================================
    # ==============================================================================
    # CONNECTION & COMMUNICATION
    # ==============================================================================
    # ==============================================================================

    def onConnect(self, request):
        """print client info on connection"""
        print("Client connecting: {}".format(request.peer))

    def onClose(self, wasClean, code, reason):
        """print reason on connection closes"""
        print("WebSocket connection closed: {}".format(reason))

    def onMessage(self, payload, isBinary):
        """process the income messages"""
        result = self.process(payload)
        self.sendMessage(result.encode(), isBinary)

    def callback(self, id_, *args, **kwargs):
        """send the arguments of callback functions to client side"""
        data = [{'callback': {'id': id_, 'args': args, 'kwargs': kwargs}}]
        istring = json.dumps(data, cls=DataEncoder)
        self.sendMessage(istring.encode())

    # NEW
    def send(self, data):
        """generic sender"""
        data = [data]
        istring = json.dumps(data, cls=DataEncoder)
        self.sendMessage(istring.encode())

    # ==============================================================================
    # ==============================================================================
    # UTILITIES
    # ==============================================================================
    # ==============================================================================

    def as_type(self, to_cast, as_type):
        """Convert data before returning to, or after recieving from client"""
        if as_type is not None and isinstance(as_type, dict):
            if 'dtype_' in as_type:
                dtype = as_type['dtype_']

                cls_ = cls_from_dtype(dtype)

                if hasattr(cls_, 'from_data') and hasattr(cls_, 'to_data'):
                    return cls_.from_data(to_cast.to_data())
                else:
                    try:
                        return cls_(to_cast)
                    except Exception as e:
                        print(str(e))
            else:
                raise ValueError(f'Unrecognised dtype object: {dtype}...')
        else:
            return to_cast

    def update_timestamps(self, id_, dkey=None, channel=0,
                          created=False, accessed=False):
        """update timestamps associated with cached data
        note: channel creation time set at creation"""

        ts = timestamp()

        if created:
            self.logs['times']['created']['by_id'][id_] = ts
            if dkey is not None:
                dk_exists = dkey in self.cached_dkeys
                if not dk_exists:
                    self.logs['times']['created']['by_dkey'][dkey] = ts

        if accessed:
            self.logs['times']['accessed']['by_id'][id_] = ts
            self.logs['times']['accessed']['by_channel'][channel] = ts
            if dkey is not None:
                self.logs['times']['accessed']['by_dkey'][dkey] = ts

    def get_cached_object_attributes(self, cached_obj, cached_ref_obj):

        cls_ = cached_obj.__class__

        attrs = []
        attrs_to_ignore = []

        # Class attributes
        for _attr_name in dir(cls_):
            if not is_class_method(cls_, _attr_name) and not is_static_method(cls_, _attr_name):
                _attr = getattr(cls_, _attr_name)
                if callable(_attr):
                    attrs.append((_attr_name, 'method'))
                elif isinstance(_attr, property):
                    attrs.append((_attr_name, 'property'))
            else:
                attrs_to_ignore.append(_attr_name)

        # Instance attributes
        attrs_to_ignore = attrs_to_ignore + list(map(lambda x: x[0], attrs))
        for _attr_name in dir(cached_obj):
            if _attr_name not in attrs_to_ignore:
                _attr = getattr(cached_obj, _attr_name)
                if callable(_attr):
                    attrs.append((_attr_name, 'method'))
                else:
                    attrs.append((_attr_name, 'attribute'))

        cached_ref_obj['protocol'] = 2
        cached_ref_obj['attributes'] = attrs
        cached_ref_obj['class_name'] = cls_.__name__

    # ==============================================================================
    # ==============================================================================
    # STORED METADATA
    # ==============================================================================
    # ==============================================================================

    # Entites
    # ------------------------------------------------------------------------------

    @property
    def cached_ids(self):
        return list(self.logs['cached']['id_to_channel'].keys())

    @property
    def cached_dkeys(self):
        return list(self.logs['cached']['dkey_to_id'].keys())

    @property
    def channels(self):
        return list(self.cached.keys())

    # Query
    # ------------------------------------------------------------------------------

    def has_cached(self, cached_ref_obj):
        id_ = cached_ref_obj['cached']
        return id_ in self.cached_ids or id_ in self.cached_dkeys

    def get_cached_id(self, cached_ref_obj):
        id_ = cached_ref_obj['cached']
        if id_ in self.cached_ids:
            # id_ is id
            pass
        elif id_ in self.cached_dkeys:
            # id_ is dkey
            cached_ref_obj['dkey'] = id_
            id_ = cached_ref_obj['cached'] = self.dkey_to_id(id_)
        else:
            raise KeyError(f'Cached ID or DKey: {id_} does not exist....')
        return id_

    # Maps
    # ------------------------------------------------------------------------------

    def id_to_channel(self, id_):
        return self.logs['cached']['id_to_channel'][id_]

    def id_to_dkey(self, id_):
        return self.logs['cached']['id_to_dkey'].get(id_, None)

    def dkey_to_id(self, dkey):
        return self.logs['cached']['dkey_to_id'][dkey]

    # Directory service...
    # ------------------------------------------------------------------------------

    # TODO: View directory of what is currently stored...
    def view(self, data):
        return self.cached_ids

    def view_dkeys(self, data):
        return self.cached_dkeys

    # ==============================================================================
    # ==============================================================================
    # GETTING
    # ==============================================================================
    # ==============================================================================

    def get_cached_arguments(self, data):
        """detect and load cached data or callback functions in arguments"""
        data['args'] = list(data['args']) # tuple args -> list args (because encoder preserves tuple)
        for _i, _a in enumerate(data['args']):
            if isinstance(_a, dict):
                if 'cached' in _a:
                    data['args'][_i] = self.get(_a)

        for _k, _a in data['kwargs'].items():
            if isinstance(_a, dict):
                if 'cached' in _a:
                    data['kwargs'][_k] = self.get(_a)
                elif 'callback' in _a:
                    # print('detected callback...')
                    _id = _a['callback']['id']
                    data['kwargs'][_k] = _callback = lambda *args, **kwargs: self.callback(_id, *args, **kwargs)
                    self.cache(_callback, id_=_id, cache_protocol=1, channel=data['channel'])

    def get(self, data):
        """get cached data from its id"""

        # called internally from server by function using dkey
        if not isinstance(data, dict):
            data, from_server = {'get': {'cached': data}}, True
        # called internally from server by args, kwargs parsers
        elif ('get' not in data and 'cached' in data):
            data, from_server = {'get': data}, True
        # retrieving cached for proxy client
        else:
            data, from_server = data, False

        cached_ref_obj = data['get']

        id_ = self.get_cached_id(cached_ref_obj)
        chnl, dk = self.id_to_channel(id_), self.id_to_dkey(id_)

        cached = self.cached[chnl][id_]

        self.update_timestamps(id_, dkey=dk, channel=chnl, accessed=True)
        cached = self.as_type(cached, data.get('as_type', None))

        data['get'] = cached

        if data.get('as_cache', False):
            self.get_cached_object_attributes(cached, cached_ref_obj)
            return cached_ref_obj

        return data if not from_server else data['get']

    def get_timestamps(self, data):

        if 'get' in data:
            cached_ref_obj = data['get']
            id_ = self.get_cached_id(cached_ref_obj)
            if 'dkey' not in cached_ref_obj:
                return {'created': self.logs['times']['created']['by_id'][id_],
                        'accessed': self.logs['times']['accessed']['by_id'][id_]}
            else:
                # Client provided dkey as reference
                return {'created': self.logs['times']['created']['by_dkey'][id_],
                        'accessed': self.logs['times']['accessed']['by_dkey'][id_]}

        elif 'channel' in data:
            return {'created': self.logs['times']['created']['by_channel'][id_],
                    'accessed': self.logs['times']['accessed']['by_channel'][id_]}

        return self.cached_timestamps[id_]

    def update_settings(self, data):
        updates = data['settings']
        self.settings.update(updates)
        return True

    # ==============================================================================
    # ==============================================================================
    # DATA MANAGEMENT
    # ==============================================================================
    # ==============================================================================

    # Cached Objects
    # ==============================================================================

    def cache_from_file(self, data):

        dtype = data.get('dtype_')
        fp = data.get('file_path')
        if dtype is None:
            with open(fp, 'r') as fp:
                loaded = json.load(fp, cls=DataDecoder)
        else:
            cls_ = cls_from_dtype(dtype)
            mtd = data.get('method')
            mtd_ = getattr(cls_, mtd)
            loaded = mtd_(fp)
        data['to_cache'] = loaded

    def cache(self, data,
              id_=None, dkey=None, cache_protocol=1, channel=0,
              as_type=None, replace=False):
        """cache received data and return its reference object"""

        if isinstance(data, dict) and 'cache' in data:
            to_cache = data['to_cache']
            cache_protocol = data['cache']
            dkey = data.get('dkey', dkey)
            channel = data.get('channel', channel)
            # replace = data.get('replace', replace)
            as_type = data.get('as_type', as_type)
        else:
            to_cache = data

        to_cache = self.as_type(to_cache, as_type)

        if id_ is None:
            id_ = id(to_cache)

        # Cache object...
        self.setup_channel(channel)
        self.cached[channel][id_] = to_cache

        self.update_timestamps(id_, dkey=dkey, channel=channel,
                               created=True, accessed=True)

        self.logs['cached']['id_to_channel'][id_] = channel

        # Remove an existing cached object with the same dkey (if requested)
        # TODO: Move this and next set of code out as 'def name_cached_object'
        if replace and dkey is not None and dkey in self.cached_dkeys:
            self.cached_dkeys[dkey]
            id_old = self.dkey_to_id(dkey)
            self.remove_cached(id_old)

        if dkey is not None:
            self.logs['cached']['dkey_to_id'][dkey] = id_
            self.logs['cached']['id_to_dkey'][id_] = dkey

        cached_ref_obj = {'cached': id_, 'protocol': cache_protocol}

        if cache_protocol >= 2:  # used to instantiate cached object wrapper
            self.get_cached_object_attributes(to_cache, cached_ref_obj)

        return cached_ref_obj

    def cache_func(self, data):
        """cache a excutable function"""
        name = data['func_to_cache']['name']
        exec(data['func_to_cache']['source'])
        exec('self.cached[name] = {}'.format(name))
        return {'cached_func': name}

    # Channels
    # ==============================================================================

    def setup_channel(self, channel=0):
        if channel not in self.cached:
            self.cached[channel] = OrderedDict()
            self.logs['times']['created']['by_channel'][channel] = timestamp()
            self.logs['times']['accessed']['by_channel'][channel] = timestamp()

    # Removing
    # ==============================================================================

    def _remove_cached(self, cached_ref_obj):
        cached_ref_obj = cached_ref_obj if (isinstance(cached_ref_obj, dict) and 'cached' in cached_ref_obj) else {'cached': cached_ref_obj}
        try:
            id_ = self.get_cached_id(cached_ref_obj)
        except KeyError:
            pass
        else:
            chnl, dk = self.id_to_channel(id_), self.id_to_dkey(id_)
            del self.cached[chnl][id_]
            del self.logs['cached']['id_to_channel'][id_]
            if dk:
                del self.logs['cached']['dkey_to_id'][dk]
                del self.logs['cached']['id_to_dkey'][id_]

    def remove_channel(self, channel):
        ids_in_chnl = list(self.cached[channel].keys())
        for _c_id in ids_in_chnl:
            self._remove_cached(_c_id)
        del self.cached[channel]

    def remove_cached(self, data):
        cached_ref_objs = data['to_remove']
        cached_ref_objs = [cached_ref_objs] if not isinstance(cached_ref_objs, list) else cached_ref_objs
        print(f"Clear cache: {cached_ref_objs}")

        for _c_ref_obj in cached_ref_objs:
            if not isinstance(_c_ref_obj, dict) and isinstance(_c_ref_obj, str):
                if _c_ref_obj == 'all':
                    self.cached.clear()
                    self.logs = deepcopy(self.default_logs)
                    return
                elif _c_ref_obj in self.channels:
                    self.remove_channel(_c_ref_obj)
            elif isinstance(_c_ref_obj, dict):
                self._remove_cached(_c_ref_obj)

    # ==============================================================================
    # ==============================================================================
    # EXECUTING METHODS / FUNCTIONS
    # ==============================================================================
    # ==============================================================================

    # ==============================================================================
    # Helpers
    # ==============================================================================

    def _resolve_settings(self, settings_key, value):
        # Use saved override settings if available
        # Useful especially for cases when working with ObjectProxy where arguments cannot be provided
        value_ = value if settings_key not in self.settings else self.settings[settings_key]
        value_ = value_ or value
        return value_

    def _prepare_namespace(self, reset=False):
        ns = self.sandbox
        if reset:
            ns.clear()
        ns.update({'cloud_server': self})
        return ns

    def _parse_output(self, output, data):
        # check for settings override
        cache_protocol = self._resolve_settings('cache_protocol', data['cache'])

        # single-value output that are instances of builtins are always returned without caching
        if is_builtins_instance(output):
            cache_protocol = 0

        if cache_protocol > 0:
            output = {'to_cache': output,
                      'cache': cache_protocol, 'dkey': data['dkey']}
            output = self.cache(output)

        elif cache_protocol == -1:
            # discard results
            output = None

        return output

    def _execute(self, func, data):

        self.get_cached_arguments(data)

        if data.get('pass_server', False):
            data['kwargs'].update({'cloud_server': self})

        start = time.time()
        res = func(*data['args'], **data['kwargs'])

        t = time.time() - start
        print('finished in: {}s'.format(t))

        return res

    # ==============================================================================
    # Main Execution Types
    # ==============================================================================

    def execute_function(self, data):
        """execute corresponding binded functions with received arguments"""
        func = get_function(data)

        print(f"<<Executed function from '{data['package']}'...>>")

        res = self._execute(func, data)
        res = self._parse_output(res, data)
        return res

    def execute_method(self, data):
        """run a method of a cached object"""
        attr_name, attr_type = data['attr']
        cached = data['get']

        if attr_type != 'setter':
            # Access data setter
            res = attr = getattr(cached, attr_name)
            # TODO: allow caching?

            if attr_type == 'method':
                res = self._execute(attr, data)

            res = self._parse_output(res, data)

        else:
            self.get_cached_arguments(data)
            setattr(cached, attr_name, *data['args'])  # kwargs?
            res = None

        cached_name = parse_name(cached)
        print(f"<<Executed '{attr_name}' of '{cached_name}'...>>")

        return res

    def execute_expression(self, data):
        """provides a sandbox environment for execution of code in server-side
        User may access server via '_sever'
        """
        ns = self._prepare_namespace(data['reset'])
        code = compile(data['expression'], '<string>', 'exec')
        exec(code, ns)

        return None

    # ==============================================================================
    # ==============================================================================
    # CONTROL
    # ==============================================================================
    # ==============================================================================

    def sessions_alive(self):
        return isinstance(self.sessions, Sessions)

    def control(self, data):
        command = data['control']
        if command == 'shutdown':
            raise KeyboardInterrupt
        if command == 'check':
            print('check from client')
            return {'status': "I'm good"}
        raise ValueError("Unrecognised control command")

    def control_sessions(self, data):
        """control attached sessions according to message received"""
        s = data["sessions"]
        if s["command"] == 'create':
            if not self.sessions_alive():
                self.sessions = Sessions(socket=self)
                return "session successfully created"
            else:
                raise RuntimeError("There is already sessions running, try to reconnect or shut down")
        else:
            if not self.sessions_alive():
                raise RuntimeError("There no running sessions, try to create one first")

            if s["command"] == 'add_task':
                funcid_ = s['func']['cached_func']
                func = self.cached[funcid_]
                self.sessions.add_task(func, *s['args'], *s['kwargs'])
                return "task added"

            if s["command"] == 'start':
                self.sessions.start()
                return "sessions started"

            if s["command"] == 'listen':
                self.sessions.listen()
                self.sessions = None
                return "All sessions concluded"

            if s["command"] == 'shutdown':
                self.sessions.terminate()
                self.sessions = None

    # ==============================================================================
    # ==============================================================================
    # PROCESS REQUEST
    # ==============================================================================
    # ==============================================================================

    def log_request(self, data):
        ts = timestamp()
        entry = {ts: data}
        self.logs['requests'].update(entry)

    def process(self, data):
        """process received data according to its content"""
        data = json.loads(data, cls=DataDecoder)[0]

        if self.settings['save_requests']:
            self.log_request(data)

        print('Received request...')

        result = None  # in case custom request was sent
        try:
            # ordering is important!

            if data.get('request') == 'cache_from_file':
                # README: must precede 'cache'
                result = self.cache_from_file(data)

            if data.get('request', '').startswith('cache') and 'to_cache' in data:
                result = self.cache(data)

            if data.get('request') == 'cache' and 'func_to_cache' in data:
                result = self.cache_func(data)

            if data.get('request') == 'remove_cached':
                result = self.remove_cached(data)

            if data.get('request') == 'settings':
                result = self.update_settings(data)

            if data.get('request') == 'get_channel_latest':
                # README: must precede 'get'
                chnl = data['channel']
                id_ = list(self.cached[chnl].keys())[-1]
                data['get'] = {'cached': id_}

            if 'get' in data:
                # README: must precede 'run_function' & 'run_method'
                if data.get('request') == 'has_cached':
                    result = self.has_cached(data['get'])
                elif data.get('request') == 'get_timestamps':
                    result = self.get_timestamps(data)
                else:
                    result = self.get(data)

            if data.get('request') == 'run_function':
                result = self.execute_function(data)

            if data.get('request') == 'run_method':
                result = self.execute_method(data)

            if data.get('request') == 'run_expression':
                result = self.execute_expression(data)

            if data.get('request') == 'view':
                result = self.view(data)

            if data.get('request') == 'view_dkeys':
                result = self.view_dkeys(data)

            if 'sessions' in data:
                result = self.control_sessions(data)

            if 'control' in data:
                result = self.control(data)

            if 'version' in data:
                result = self.version()

        except BaseException as error:

            if isinstance(error, KeyboardInterrupt):
                raise KeyboardInterrupt

            exc_type, exc_value, exc_tb = sys.exc_info()
            result = {'error': traceback.format_exception(exc_type, exc_value, exc_tb)}
            print("".join(result['error']))

        print('=' * 80)
        print()

        istring = json.dumps([result], cls=DataEncoder)
        return istring

    def version(self):

        working_set = pkg_resources.working_set
        packages = set([p.project_name for p in working_set]) - set(['COMPAS'])
        compas_pkgs = [p for p in packages if p.lower().startswith('compas')]

        return {
            "COMPAS":       compas.__version__,
            "Python":       sys.version,
            "Extensions":   compas_pkgs
        }


if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser(description='Start compas_struct_ml_proxy...')
    parser.add_argument("-p", "--port", default=cc.CLOUD_DEFAULTS['port'], type=int, action='store', dest='port', help='Port to connect...')
    args = parser.parse_args()

    try:
        import asyncio
    except ImportError:
        # Trollius >= 0.3 was renamed
        import trollius as asyncio

    from autobahn.asyncio.websocket import WebSocketServerFactory
    factory = WebSocketServerFactory()
    factory.protocol = CompasServerProtocol

    ip = '127.0.0.1'
    port = args.port

    loop = asyncio.get_event_loop()
    coro = loop.create_server(factory, '127.0.0.1', port)
    server = loop.run_until_complete(coro)
    print("Starting compas_cloud server")
    print("Listening at %s:%s" % (ip, port))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        print("Shuting down server")
        server.close()
        loop.close()
