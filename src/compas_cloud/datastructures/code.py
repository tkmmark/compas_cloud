import compas
from compas.base import Base

if not compas.IPY:
    import inspect

    def get_caller(level_in=0):
        return inspect.getmodule(inspect.stack()[1 + int(level_in)][0])

    def set_module_attrs_as_locals(module):
        mod_caller = get_caller() #inspect.getmodule(inspect.stack()[1][0])
        attrs = [_attr for _attr in dir(module) if not _attr.startswith('__') and '__' not in _attr]
        [setattr(mod_caller, _attr, getattr(module, _attr)) for _attr in attrs]


# class Code(Base):
#     def __init__(self, code):
#         assert isinstance(code, str)
#         self.data = code

#     def to_data(self):
#         return self.data

#     @classmethod
#     def from_data(cls, data):
#         return cls(data)

#     def __call__(self, **kwargs):
#         if not compas.IPY:
#             caller = get_caller()
#             set_module_attrs_as_locals(caller)
#             exec(compile(self.data, "-", "exec"))
#         else:
#             return self

class Code(Base):
    def __init__(self, src: str, 
                       code: str=None, 
                       attr: str=None):
        """code: '
           src:   'file', or 'string' """
        self._src = src
        self._code = code
        self._attr = attr

    def load_code_from_string(self):
        ns = {}
        exec(self._code, ns)
        attr = self._attr or list(ns.keys())[0]  # assume 
        self._func = ns[attr]

    def load_code_from_file(self):
        fp = self._code if os.path.exists(self._code) else None
        if file_path:
            f = open(fp)
            self._code = f.read()
            self.load_code_from_string()

    @property
    def function(self):
        if self._src == 'file':
            self.load_code_from_file()
        elif self._src == 'string':
            self.load_code_from_string()
        return self._func

    def __call__(self, *args, **kwargs):
        return self.function

    @property
    def data(self):
        return {'src': self.src, 'code': self.code, 'attr': self.attr}

    @data.setter
    def data(self, data):
        self._src = data['src']
        self._code = data['code']
        self._attr = data['attr']

    def to_data(self):
        return self._ata

    @classmethod
    def from_data(cls, data):
        cls(src=data['src'], 
            code=data['code'], 
            attr=data['attr'])


# ==============================================================================
# Main
# ==============================================================================

if __name__ == '__main__':

    str_ = """
def foo(x, y):
    print ("testf called with %s, %s"%(x,y))
    """
    foo_ = Code(src='string', code=str_, attr='foo')
    foo_.function('1', '2')

