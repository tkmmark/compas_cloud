# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import json
from ast import literal_eval

from datetime import datetime

__all__ = ['cls_from_dtype', 'DataDecoder', 'DataEncoder']


class DecoderError(Exception):
    pass

def cls_from_dtype(dtype):
    """Get the class object corresponding to a COMPAS data type specification.

    Parameters
    ----------
    dtype : str
        The data type of the COMPAS object in the following format:
        '{}/{}'.format(o.__class__.__module__, o.__class__.__name__).

    Returns
    -------
    :class:`compas.base.Base`

    Raises
    ------
    ValueError
        If the data type is not in the correct format.
    ImportError
        If the module can't be imported.
    AttributeError
        If the module doesn't contain the specified data type.

    """

    mod_name, attr_name = dtype.split('/')
    module = __import__(mod_name, fromlist=[attr_name])
    return getattr(module, attr_name)


class DataEncoder(json.JSONEncoder):
    """Data encoder for custom JSON serialisation with support for COMPAS data structures and geometric primitives.

    Notes
    -----
    In the context of Remote Procedure Calls,

    """

    def encode(self, o):
        def tuples_encoder(item):
            if isinstance(item, tuple):
                return {'__tuple__': True, 'items': item}
            elif isinstance(item, list):
                return [tuples_encoder(e) for e in item]
            elif isinstance(item, dict):
                return {key: tuples_encoder(value) for key, value in item.items()}
            else:
                return item

        return super(DataEncoder, self).encode(tuples_encoder(o))

    def default(self, o):
        try:
            value = o.to_data()
        except AttributeError:
            pass
        else:
            # in cases when DataEncoder is called by json.dump (e.g. via to_json()),
            # this ensures that the data dict will also be jsonised using this custom default,
            # otherwise, the data dict will be jsonised using the default default
            value = json.dumps(value, cls=DataEncoder)
            data = {'dtype': "{}/{}".format(".".join(o.__class__.__module__.split(".")[:]), o.__class__.__name__), 'value': value}
            return data

        if hasattr(o, '__next__'):
            return list(o)

        if isinstance(o, datetime):
            return {'__datetime__': True, 'data': o.isoformat()}

        if isinstance(o, set):
            return {'__set__': True, 'data': json.dumps(list(o), cls=DataEncoder)}

        try:
            import numpy as np
        except ImportError:
            pass
        else:
            if isinstance(o, np.ndarray):
                return o.tolist()
            if isinstance(o, (np.int32, np.int64)):
                return int(o)
            if isinstance(o, (np.float32, np.float64)):
                return float(o)

            elif isinstance(o, (np.int_, np.intc, np.intp, np.int8,
                                np.int16, np.int32, np.int64, np.uint8,
                                np.uint16, np.uint32, np.uint64)):
                return int(o)

            elif isinstance(o, (np.float_, np.float16, np.float32, np.float64)):
                return float(o)

            elif isinstance(o, np.bool_):
                return bool(o)

            elif isinstance(o, np.void):
                return None

        try:
            from torch import Tensor
        except ImportError:
            pass
        else:
            if isinstance(o, Tensor):
                return o.tolist()

        return super(DataEncoder, self).default(o)


class DataDecoder(json.JSONDecoder):
    """Data decoder for custom JSON serialisation with support for COMPAS data structures and geometric primitives."""

    def __init__(self, *args, **kwargs):
        super(DataDecoder, self).__init__(object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, o):

        if 'dtype' in o:

            try:
                cls = cls_from_dtype(o['dtype'])

            except ValueError:
                print(DecoderError("The data type of the object should be in the following format: '{}/{}'.format(o.__class__.__module__, o.__class__.__name__)"))

            except ImportError:
                raise DecoderError("The module of the data type '{}' can't be found.".format(o['dtype']))

            except AttributeError:
                raise DecoderError("The data type '{}' can't be found in the specified module.".format(o['dtype']))

            else:
                from pprint import pprint

                if 'value' in o:
                    data = o.get('value')
                    if isinstance(data, str):
                        return cls.from_data(json.loads(data, cls=DataDecoder))
                    elif isinstance(data, dict):
                        return cls.from_data(data)

        if '__tuple__' in o:

            return tuple(o['items'])

        if '__datetime__' in o:

            return datetime.fromisoformat(o['data'])

        if '__set__' in o:
            print(o['data'])
            return set(json.loads(o['data'], cls=DataDecoder))

        else:

            o_ = {}
            for k, v in o.items():
                try:
                    k_ = literal_eval(k)
                except (ValueError, SyntaxError) as e:
                    k_ = k
                finally:
                    o_[k_] = v
            return o_


# ==============================================================================
# Main
# ==============================================================================

if __name__ == '__main__':
    pass

    data = [set(['a', 'b', 'a']), set([('a', 'c'), 'b', 'a'])]
    datas = json.dumps(data, cls=DataEncoder)
    data = json.loads(datas, cls=DataDecoder)
    print(data)