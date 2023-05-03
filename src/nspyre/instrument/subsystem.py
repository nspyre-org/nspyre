import logging
from typing import Dict
from typing import Union

from .server import InstrumentServer
from .gateway import InstrumentGateway
from ..gui import QObject
from ..gui import Qt_GUI
from ..gui import QtCore

_logger = logging.getLogger(__name__)


class Subsystem(QObject):
    """Generalized experimental subsystem that allows for management of
    dependencies between subsystems for boot sequencing."""

    if Qt_GUI:
        booted_sig = QtCore.Signal()
        shutdown_sig = QtCore.Signal()

    # TODO type hint for callable?
    def __init__(
        self,
        name: str,
        pre_dep_boot=None,
        post_dep_boot=None,
        default_boot_timeout: float = 10,
        default_boot_inserv: Union[InstrumentServer, InstrumentGateway] = None,
        default_boot_add_args: list = None,
        default_boot_add_kwargs: Dict = None,
        pre_dep_shutdown=None,
        post_dep_shutdown=None,
        dependencies: list = None,
    ):
        """
        Args:
            name: Subsystem name.
            pre_dep_boot: Function to run before booting any dependency 
                subsystems; should take 1 argument, which is the subsystem 
                object.
            post_dep_boot: Function to run to boot the subsystem after booting
                any dependency subsystems; should take 1 argument, which is the
                subsystem object. If None, :py:meth:`default_boot` will be used.
            default_boot_timeout: Time to wait (s) for the driver to initialize
                in :py:meth:`default_boot`.
            default_boot_inserv: :py:class:`~nspyre.instrument.InstrumentServer`
                (or a connected :py:class:`~nspyre.instrument.InstrumentGateway`)
                to add the driver to in :py:meth:`default_boot`.
            default_boot_args: Arguments to pass to the
                :py:class:`~nspyre.instrument.InstrumentServer`
                :py:meth:`~nspyre.instrument.InstrumentServer.add` method to
                create the driver in :py:meth:`default_boot`.
            default_boot_args: Keyword arguments to pass to the
                :py:class:`~nspyre.instrument.InstrumentServer`
                :py:meth:`~nspyre.instrument.InstrumentServer.add` method to
                create the driver in :py:meth:`default_boot`.
            pre_dep_shutdown: Function to run once shutdown is requested, but
                before shutting down any dependencies; should take 1 argument,
                which is the subsystem object. If None,
                :py:meth:`default_shutdown` will be used.
            post_dep_shutdown: Function to run after shutting down any
                dependencies; should take 1 argument, which is the subsystem
                object.
            dependencies: List of Subsystem objects this subsystem depends on;
                they will be booted (in order) before this subsystem, and
                shutdown (in reverse order) after this subsystem shuts down.
        """
        super().__init__()

        # subsystem name
        self.name = name

        # dependency subsystem
        if dependencies is None:
            self.dependencies = []
        else:
            self.dependencies = dependencies

        # dependent subsystems
        self.dependents = []
        if dependencies is not None:
            # set self as a dependent for all dependencies
            for subsys in self.dependencies:
                subsys.dependents.append(self)

        self.pre_dep_boot = pre_dep_boot
        self.post_dep_boot = post_dep_boot
        self.default_boot_timeout = default_boot_timeout
        self.default_boot_inserv = default_boot_inserv
        if default_boot_add_args is None:
            self.default_boot_add_args = []
        else:
            self.default_boot_add_args = default_boot_add_args
        if default_boot_add_kwargs is None:
            self.default_boot_add_kwargs = []
        else:
            self.default_boot_add_kwargs = default_boot_add_kwargs
        self.pre_dep_shutdown = pre_dep_shutdown
        self.post_dep_shutdown = post_dep_shutdown
        self.booted = False

    def __str__(self):
        return f'{self.name} (booted={self.booted})'

    def default_boot(self):
        """Tries to add the driver to the :py:class:`~nspyre.instrument.InstrumentServer`
        in a loop, until :py:attr:`default_boot_timeout` has elapsed."""
        if self.default_boot_inserv is None:
            raise ValueError('If using default_boot, an InstrumentServer or InstrumentGateway must be provided using the default_boot_inserv keyword argument.')
        timeout = time.time() + self.default_boot_timeout
        while True:
            try:
                self.default_boot_inserv.add(*self.default_boot_add_args, **self.default_boot_add_kwargs)
                break
            except Exception as err:
                if time.time() > timeout:
                    raise TimeoutError(f'Failed initializing driver for subsystem [{self.name}].') from err
                time.sleep(0.5)

    def default_shutdown(self):
        """Remove the driver from the :py:class:`~nspyre.instrument.InstrumentServer`."""
        if 'name' in self.default_boot_add_kwargs:
            name = self.default_boot_add_kwargs['name']
        else:
            name = self.default_boot_add_args[0]
        self.default_boot_inserv.remove(name)

    def boot(self, boot_dependencies: bool = True):
        if self.booted:
            _logger.warning(
                f'Ignoring boot request for [{self.name}] because it is already booted.'
            )
            return
        _logger.info(f'Booting [{self.name}]...')

        if self.pre_dep_boot is not None:
            self.pre_dep_boot(self)

        # make sure all dependencies are booted before booting
        for subsys in self.dependencies:
            if not subsys.booted:
                if boot_dependencies:
                    subsys.boot(boot_dependencies=True)
                else:
                    _logger.warning(
                        f'Cancelling boot request for [{self.name}] because dependency [{subsys.name}] is not booted.'
                    )
                    return

        if self.post_dep_boot is not None:
            self.post_dep_boot(self)
        else:
            self.default_boot()

        self.booted = True
        if Qt_GUI:
            self.booted_sig.emit(self.booted)
        _logger.info(f'Booted [{self.name}].')

    def shutdown(self, shutdown_dependencies: bool = True):
        """Shutdown the subsystem.

        Args:
            shutdown_dependencies: if True, shutdown all dependencies after shutting down
        """
        if not self.booted:
            _logger.warning(
                f'Ignoring shutdown request for [{self.name}] because it is not booted.'
            )
            return
        _logger.info(f'Shutting down [{self.name}]...')

        # make sure all dependents are shutdown before shutting down
        for subsys in self.dependents:
            if subsys.booted:
                _logger.warning(
                    f'Cancelling shutdown request for [{self.name}] because subsystem dependent [{subsys.name}] is still booted.'
                )
                return

        if self.pre_dep_shutdown is not None:
            self.pre_dep_shutdown(self)
        else:
            self.default_shutdown()

        self.booted = False
        if Qt_GUI:
            self.shutdown_sig.emit()
        _logger.info(f'Shutdown [{self.name}].')

        if shutdown_dependencies:
            # shutdown all dependencies in reverse order after shutting down
            for subsys in reversed(self.dependencies):
                if subsys.booted:
                    # only shutdown the dependency if it has no other booted dependents
                    should_shutdown = True
                    for d in subsys.dependents:
                        if d.booted:
                            _logger.info(
                                f'Not shutting down [{subsys.name}] because its dependent [{d.name}] is still booted.'
                            )
                            should_shutdown = False
                    if should_shutdown:
                        subsys.shutdown(shutdown_dependencies=True)

        if self.post_dep_shutdown is not None:
            self.post_dep_shutdown(self)
