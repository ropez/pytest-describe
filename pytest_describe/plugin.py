import imp
import sys
import types
import pytest


def trace_function(funcobj, *args, **kwargs):
    """Call a function, and return its locals"""
    funclocals = {}

    def _tracefunc(frame, event, arg):
        if event == 'call':
            # Activate local trace for first call only
            if frame.f_back.f_locals.get('_tracefunc') == _tracefunc:
                return _tracefunc
        elif event == 'return':
            funclocals.update(frame.f_locals)

    sys.settrace(_tracefunc)
    try:
        funcobj(*args, **kwargs)
    finally:
        sys.settrace(None)

    return funclocals


def make_module_from_function(funcobj):
    """Evaluates the local scope of a function, as if it was a module"""
    module = imp.new_module(funcobj.__name__)
    module.__dict__.update(trace_function(funcobj))
    return module


class DescribeBlock(pytest.Module):
    """Module-like object representing the scope of a describe block"""

    def __init__(self, funcobj, path, parent):
        super(DescribeBlock, self).__init__(path, parent)
        self.funcobj = funcobj

    def _makeid(self):
        """Magic that makes fixtures local to each scope"""
        return self.parent.nodeid + '::' + self.funcobj.__name__

    def _importtestmodule(self):
        """Import a describe block as if it was a module"""
        return make_module_from_function(self.funcobj)

    def funcnamefilter(self, name):
        """Treat all nested functions as tests, without requiring the 'test_' prefix"""
        return not name.startswith('describe_') and not name.startswith('_')

    def classnamefilter(self, name):
        """Don't allow test classes inside describe"""
        return False

    def __repr__(self):
        return "<{} {}>".format(self.__class__.__name__,
                                repr(self.funcobj.__name__))


def pytest_pycollect_makeitem(__multicall__, collector, name, obj):
    res = __multicall__.execute()
    if res is not None:
        return res

    is_func = isinstance(obj, types.FunctionType)
    if is_func and obj.__name__.startswith('describe_'):
        return DescribeBlock(obj, collector.fspath, collector)