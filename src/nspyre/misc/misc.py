"""
A collection of miscellaneous functionality.
"""
import functools
import importlib
import inspect
import logging
import sys
import warnings
from multiprocessing import Process
from pathlib import Path
from typing import Type


logger = logging.getLogger(__name__)


# root directory of nspyre
NSPYRE_ROOT = Path(__file__).parent.parent


def join_nspyre_path(path) -> Path:
    """Return a path from a path given relative to the nspyre root
    directory.

    Args:
        path: Path object relative to the nspyre root.

    Returns:
        The absolute path.
    """
    return (NSPYRE_ROOT / path).resolve()


# images
LOGO_PATH = str(join_nspyre_path('gui/images/spyre.png'))


def _deprecated(reason):
    """
    This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used.
    """

    string_types = (type(b''), type(u''))
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


def _load_class_from_str(class_str: str) -> Type:
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


def _load_class_from_file(file_path: Path, class_name: str) -> Type:
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


class ProcessRunner:
    """Run a function in a new process."""

    def __init__(self, kill=True):
        """
        Args:
            kill: Whether to kill a previously running process that hasn't completed.

        """
        self.proc = None
        self.should_kill = kill

    def run(self, fun, *args, **kwargs):
        """Run the provided function in a separate process.

        Args:
            fun: Function to run.
            args: Arguments to pass to fun.
            kwargs: Keyword arguments to pass to fun.

        Raises:
            RuntimeError: The function from a previous call is still running.

        """
        if self.running():
            if self.should_kill:
                logger.info('Previous function is still running. Killing it...')
                self.kill()
            else:
                raise RuntimeError('Previous function is still running.')

        logger.info(
            f'Running process function [{fun}] with args: [{args}] kwargs: [{kwargs}].'
        )
        self.proc = Process(target=fun, args=args, kwargs=kwargs, daemon=True)
        self.proc.start()

    def running(self):
        """Return True if the process is running."""
        return self.proc is not None and self.proc.is_alive()

    def kill(self):
        """Kill the process."""
        if self.proc:
            logger.info('Killing process.')
            self.proc.terminate()
            self.proc.join()
            self.proc = None
