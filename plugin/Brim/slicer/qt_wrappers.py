import contextlib
import types

WRAPPER_NAME = "_call_on_qt_thread_wrapper"


def unwrapped(bound, name):
    function = getattr(bound, "__func__", None)
    if function is None or function.__name__ != WRAPPER_NAME:
        return bound
    for cell in function.__closure__ or ():
        inner = cell.cell_contents
        if isinstance(inner, types.FunctionType) and inner.__name__ == name:
            return types.MethodType(inner, bound.__self__)
    return bound


@contextlib.contextmanager
def direct_qt_calls(target, *names):
    shadowed = []
    for name in names:
        bound = getattr(target, name, None)
        direct = unwrapped(bound, name)
        if direct is not bound and name not in vars(target):
            setattr(target, name, direct)
            shadowed.append(name)
    try:
        yield target
    finally:
        for name in shadowed:
            delattr(target, name)
