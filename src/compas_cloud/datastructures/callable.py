
import os

import compas
from compas.base import Base

from compas_cloud.helpers.encoders import cls_from_dtype

# if not compas.IPY:
#     import inspect

#     def get_caller(level_in=0):
#         return inspect.getmodule(inspect.stack()[1 + int(level_in)][0])

#     def set_module_attrs_as_locals(module):
#         mod_caller = get_caller() #inspect.getmodule(inspect.stack()[1][0])
#         attrs = [_attr for _attr in dir(module) if not _attr.startswith('__') and '__' not in _attr]
#         [setattr(mod_caller, _attr, getattr(module, _attr)) for _attr in attrs]

# class Code(Base):
#     def __call__(self, **kwargs):
#         if not compas.IPY:
#             caller = get_caller()
#             set_module_attrs_as_locals(caller)
#             exec(compile(self.data, "-", "exec"))
#         else:
#             return self

class CodeMessenger(Base):
    def __init__(self, src: str, 
                       code: str=None, 
                       attr: str=None):
        """code: 
           src:  'file', 'string', 'import'
           attr: (optional) name of function to import in code
        """
        self._src = src
        self._code = code
        self._attr = attr
        # print(self._src, self._code, self._attr)

    def load_code_from_string(self, code=None):
        ns = {}
        exec(code or self._code, ns)
        attr = self._attr or list(ns.keys())[0]  # assume 
        self._func = ns[attr]

    def load_code_from_file(self):
        fp = self._code if os.path.exists(self._code) else None
        if fp:
            f = open(fp)
            code = f.read()
            self.load_code_from_string(code)

    def import_code(self):
        self._func = cls_from_dtype(self._code + '/' + self._attr)

    @property
    def function(self):
        if self._src == 'file':
            self.load_code_from_file()
        elif self._src == 'string':
            self.load_code_from_string()
        elif self._src == 'import':
            self.import_code()
        return self._func

    def __call__(self, *args, **kwargs):
        return self.function(*args, **kwargs)

    @property
    def data(self):
        return {'src': self._src, 'code': self._code, 'attr': self._attr}

    @data.setter
    def data(self, data):
        self._src = data['src']
        self._code = data['code']
        self._attr = data['attr']

    def to_data(self):
        return self.data

    @classmethod
    def from_data(cls, data):
        obj = cls(src=data['src'], 
                  code=data['code'], 
                  attr=data['attr'])
        print('in from_data: ', obj)
        return obj


if not compas.IPY:
    str_ = """
def foo_from_string(args):
    res = ("foo_from_string called with %s"%(args))
    print(res)
    return res

        """

def foo_from_file(args):
    res = ("foo_from_file called with %s"%(args))
    print(res)
    return res

import pprint
def codemessenger_test_func(func):
    # pprint(func)
    print('Inside function...')
    res = func('abc')
    print(res)
    print('Function executed...')
    return res

# ==============================================================================
# Main
# ==============================================================================

if __name__ == '__main__':

    # foo_str = CodeMessenger(src='string', code=str_, attr='foo_from_string')
    # foo_str.function('abc')
    from compas_cloud.datastructures.callable import CodeMessenger

    foo_import = CodeMessenger(src='import', code='compas_cloud.datastructures.callable', attr='foo_from_file')
    foo_import(123)
    exit()

    foo_file = CodeMessenger(src='file', code=str(__file__), attr='foo_from_file')
    # foo_file.function('abc')
    # print('done')
    # print(type(foo_file))

    foo_file_ = CodeMessenger.from_data(foo_file.to_data())
    # foo_file_.function('abc')
    # exit()

    if False:
        from compas_cloud.helpers.encoders import DataEncoder, DataDecoder
        import json

        dumps = json.dumps(foo_file_, cls=DataEncoder)
        foo_file__ = json.loads(dumps, cls=DataDecoder)
        exit()

    from compas_cloud import Proxy
    p = Proxy(port=9001)

    codemessenger_tester = p.function('compas_cloud.datastructures.callable.codemessenger_test_func')
    codemessenger_tester(func=foo_file)


