import functools
import importlib
import inspect
import sys
import warnings
from pathlib import Path
from typing import Type

string_types = (type(b''), type(u''))

# root directory of nspyre
NSPYRE_ROOT = Path(__file__).parent.parent


def join_nspyre_path(path):
    """Return a full path from a path given relative to the nspyre root
    directory"""
    return NSPYRE_ROOT / path


# images
LOGO_PATH = str(join_nspyre_path('gui/images/spyre.png'))


def deprecated(reason):
    """
    This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used.
    """

    if isinstance(reason, string_types):

        # The @deprecated is used with a 'reason'.
        #
        # .. code-block:: python
        #
        #    @deprecated("please, use another function")
        #    def old_function(x, y):
        #      pass

        def decorator(func1):

            if inspect.isclass(func1):
                fmt1 = "Call to deprecated class {name} ({reason})."
            else:
                fmt1 = "Call to deprecated function {name} ({reason})."

            @functools.wraps(func1)
            def new_func1(*args, **kwargs):
                warnings.simplefilter('always', DeprecationWarning)
                warnings.warn(
                    fmt1.format(name=func1.__name__, reason=reason),
                    category=DeprecationWarning,
                    stacklevel=2,
                )
                warnings.simplefilter('default', DeprecationWarning)
                return func1(*args, **kwargs)

            return new_func1

        return decorator

    elif inspect.isclass(reason) or inspect.isfunction(reason):

        # The @deprecated is used without any 'reason'.
        #
        # .. code-block:: python
        #
        #    @deprecated
        #    def old_function(x, y):
        #      pass

        func2 = reason

        if inspect.isclass(func2):
            fmt2 = "Call to deprecated class {name}."
        else:
            fmt2 = "Call to deprecated function {name}."

        @functools.wraps(func2)
        def new_func2(*args, **kwargs):
            warnings.simplefilter('always', DeprecationWarning)
            warnings.warn(
                fmt2.format(name=func2.__name__),
                category=DeprecationWarning,
                stacklevel=2,
            )
            warnings.simplefilter('default', DeprecationWarning)
            return func2(*args, **kwargs)

        return new_func2

    else:
        raise TypeError(repr(type(reason)))


def load_class_from_str(class_str: str) -> Type:
    """Load a python class object (available in the local scope)
    from a string"""
    class_name = class_str.split('.')[-1]
    module_name = class_str.replace('.' + class_name, '')

    if module_name in sys.modules:
        # we just need to reload it
        mod = importlib.reload(sys.modules[module_name])
    else:
        # load the module
        mod = importlib.import_module(module_name)

    return getattr(mod, class_name)


def load_class_from_file(file_path: Path, class_name: str) -> Type:
    """Load a python class object from an external python file"""

    # confirm the file exists
    if not file_path.is_file():
        raise FileNotFoundError(f'File "{file_path}" doesn\'t exist')

    file_dir = file_path.parent
    file_name = file_path.stem

    # load the class from its python file
    sys.path.append(str(file_dir))
    if file_name in sys.modules:
        loaded_module = importlib.reload(sys.modules[file_name])
    else:
        loaded_module = importlib.import_module(file_name)

    loaded_class = getattr(loaded_module, class_name)

    return loaded_class


def qt_set_trace():
    """Set a tracepoint in the Python debugger (pdb) that works with Qt."""
    from PyQt5.QtCore import pyqtRemoveInputHook
    from pdb import set_trace

    pyqtRemoveInputHook()
    set_trace()
