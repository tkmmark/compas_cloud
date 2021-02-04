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


class Code(Base):
    def __init__(self, code):
        assert isinstance(code, str)
        self.data = code

    def to_data(self):
        return self.data

    @classmethod
    def from_data(cls, data):
        return cls(data)

    def __call__(self, **kwargs):
        if not compas.IPY:
            caller = get_caller()
            set_module_attrs_as_locals(caller)
            exec(compile(self.data, "-", "exec"))
        else:
            return self


# ==============================================================================
# Main
# ==============================================================================

if __name__ == '__main__':
    pass
    txt = """
    def foo(x,y):
        print "testf called with %s,%s"%(x,y)
    """
