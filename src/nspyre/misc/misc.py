from collections.abc import Iterable
import functools
import importlib
import inspect
import sys
import warnings

import numpy as np
import rpyc

string_types = (type(b''), type(u''))


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
                    stacklevel=2
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
                stacklevel=2
            )
            warnings.simplefilter('default', DeprecationWarning)
            return func2(*args, **kwargs)

        return new_func2

    else:
        raise TypeError(repr(type(reason)))

# for properly serializing / deserializing quantity objects using the local
# pint unit registry
def register_quantity_brining(quantity_class):
    """Monkey-patch fix that allows the use of the pint module with RPyC. 
    Pint does not work over an RPyC connection for a few reasons. First, it
    it makes liberal uses the python type() function, which will return
    a netref if used on a Quantity object over an RPyC connection. This breaks 
    internal pint functionality. Furthermore, Pint has an associated unit 
    registry, and Quantity objects cannot be shared between registries. Because 
    Quantity objects passed from the client to server or vice versa have a 
    different unit registry, they must be converted to Quantity objects of the 
    local registry. RPyC serializes fundamental python types using "brine". 
    We will make a custom brine serializer for Quantity objects to properly 
    pack and unpack them using the provided unit registry.
    For more details, see pint documentation and
    https://github.com/tomerfiliba-org/rpyc/blob/master/rpyc/core/brine.py

    quantity_class: the Quantity class object from the local pint registry
    """
    rpyc.core.brine.TAG_PINT_Q = b"\xFA"

    # function for serializing quantity objects
    @rpyc.core.brine.register(rpyc.core.brine._dump_registry,
                                type(quantity_class(1, 'V')))
    def _dump_quantity(obj, stream):
        stream.append(rpyc.core.brine.TAG_PINT_Q)
        quantity_tuple = obj.to_tuple()
        rpyc.core.brine._dump((float(quantity_tuple[0]), \
                                quantity_tuple[1]), stream)

    # function for deserializing quantity objects
    @rpyc.core.brine.register(rpyc.core.brine._load_registry,
                            rpyc.core.brine.TAG_PINT_Q)
    def _load_quantity(stream):
        q = quantity_class.from_tuple(rpyc.core.brine._load(stream))
        return q
    rpyc.core.brine.simple_types = rpyc.core.brine.simple_types.union(\
                                    frozenset([type(quantity_class(1, 'V'))]))


def load_class_from_str(class_str):
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


def load_class_from_file(file_path, class_name):
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
    """Set a tracepoint in the Python debugger that works with Qt"""
    from PyQt5.QtCore import pyqtRemoveInputHook
    from pdb import set_trace
    pyqtRemoveInputHook()
    set_trace()
