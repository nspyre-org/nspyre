import logging
import time
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Self
from typing import Union

from ..gui import QObject
from ..gui import Qt_GUI
from ..gui import QtCore
from ..instrument.gateway import InstrumentGateway
from ..instrument.server import InstrumentServer
from ..instrument.server import InstrumentServerDeviceExistsError

_logger = logging.getLogger(__name__)


class Subsystem(QObject):
    """Generalized experimental subsystem that allows for management of \
    dependencies between subsystems for boot sequencing."""

    if Qt_GUI:
        booted_sig = QtCore.Signal()
        shutdown_sig = QtCore.Signal()

    def __init__(
        self,
        name: str,
        pre_dep_boot: Optional[Callable] = None,
        post_dep_boot: Optional[Callable] = None,
        default_boot_timeout: float = 10,
        default_boot_inserv: Optional[
            Union[InstrumentServer, InstrumentGateway]
        ] = None,
        default_boot_add_args: Optional[list] = None,
        default_boot_add_kwargs: Optional[Dict] = None,
        pre_dep_shutdown: Optional[Callable] = None,
        post_dep_shutdown: Optional[Callable] = None,
        dependencies: Optional[list] = None,
        exclusions: Optional[list] = None,
    ):
        """
        Args:
            name: Subsystem name.
            pre_dep_boot: Function to run before booting any dependency
                subsystems. It should take 1 argument, which is the subsystem
                object.
            post_dep_boot: Function to run to boot the subsystem after booting
                any dependency subsystems. It should take 1 argument, which is
                the subsystem object. If None, :py:meth:`default_boot` will be
                used.
            default_boot_timeout: Time to wait (s) for the driver to initialize
                in :py:meth:`default_boot`.
            default_boot_inserv: :py:class:`~nspyre.instrument.InstrumentServer`
                (or a connected :py:class:`~nspyre.instrument.InstrumentGateway`)
                to add the driver to in :py:meth:`default_boot`.
            default_boot_add_args: Arguments to pass to the
                :py:class:`~nspyre.instrument.InstrumentServer`
                :py:meth:`~nspyre.instrument.InstrumentServer.add` method to
                create the driver in :py:meth:`default_boot`.
            default_boot_add_kwargs: Keyword arguments to pass to the
                :py:class:`~nspyre.instrument.InstrumentServer`
                :py:meth:`~nspyre.instrument.InstrumentServer.add` method to
                create the driver in :py:meth:`default_boot`.
            pre_dep_shutdown: Function to run once shutdown is requested, but
                before shutting down any dependencies. It should take 1
                argument, which is the subsystem object. If None,
                :py:meth:`default_shutdown` will be used.
            post_dep_shutdown: Function to run after shutting down any
                dependencies. It should take 1 argument, which is the subsystem
                object.
            dependencies: List of Subsystem objects this subsystem depends on.
                They will be booted (in order) before this subsystem, and
                shutdown (in reverse order) after this subsystem shuts down.
            exclusions: List of Subsystem objects that exclude this Subsystem
                from being booted. This Subsystem will only boot if all
                Subsytems in exclusions are not booted. Note that this does not
                necessarily prevent this Subsystem and a Subsystem in exclusions
                from being simultaneously booted. For example, if you boot this
                Subsystem, then later boot a Subsystem in exclusions. If you
                want two Subsystems to never be booted at the same time, you
                should use :py:meth:`mutual_exclusion`.
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
        self.dependents: list[Subsystem] = []
        if dependencies is not None:
            # set self as a dependent for all dependencies
            for subsys in self.dependencies:
                subsys.dependents.append(self)

        # exclusion subsystems
        if exclusions is None:
            self.exclusions = []
        else:
            self.exclusions = exclusions

        self.pre_dep_boot = pre_dep_boot
        self.post_dep_boot = post_dep_boot
        self.default_boot_timeout = default_boot_timeout
        self.default_boot_inserv = default_boot_inserv
        if default_boot_add_args is None:
            self.default_boot_add_args = []
        else:
            self.default_boot_add_args = default_boot_add_args
        if default_boot_add_kwargs is None:
            self.default_boot_add_kwargs = {}
        else:
            self.default_boot_add_kwargs = default_boot_add_kwargs
        self.pre_dep_shutdown = pre_dep_shutdown
        self.post_dep_shutdown = post_dep_shutdown
        self.booted = False

    def __str__(self):
        return f'{self.name} (booted={self.booted})'

    def _dev_name(self):
        if 'name' in self.default_boot_add_kwargs:
            name = self.default_boot_add_kwargs['name']
        else:
            name = self.default_boot_add_args[0]
        return name

    def default_boot(self):
        """Tries to add the driver to the
        :py:class:`~nspyre.instrument.InstrumentServer` in a loop, until
        :code:`default_boot_timeout` has elapsed."""
        if self.default_boot_inserv is None:
            raise ValueError(
                'If using default_boot, an InstrumentServer or InstrumentGateway must '
                'be provided using the default_boot_inserv keyword argument.'
            )

        timeout = time.time() + self.default_boot_timeout
        while True:
            try:
                self.default_boot_inserv.add(
                    *self.default_boot_add_args, **self.default_boot_add_kwargs
                )
                break
            except InstrumentServerDeviceExistsError:
                _logger.info(
                    f'Device [{self.name}] already exists on the '
                    'instrument server. Leaving it as is and continuing.'
                )
                break
            except Exception as err:
                if time.time() > timeout:
                    raise TimeoutError(
                        f'Failed initializing driver for subsystem [{self.name}].'
                    ) from err
                time.sleep(0.5)

    def default_shutdown(self):
        """Remove the driver from the
        :py:class:`~nspyre.instrument.InstrumentServer`."""
        try:
            self.default_boot_inserv.remove(self._dev_name())
        except Exception:
            _logger.warning(f'Failed deleting [{self._dev_name()}]. Continuing...')

    def boot(self, boot_dependencies: bool = True):
        """
        Args:
            boot_dependencies: If True, boot all dependencies before booting
                this subsystem.
        """
        if self.booted:
            _logger.warning(
                f'Ignoring boot request for [{self.name}] because it is already booted.'
            )
            return
        _logger.info(f'Booting [{self.name}]...')

        for exc in self.exclusions:
            if exc.booted:
                _logger.warning(
                    f'Ignoring boot request for [{self.name}] because [{exc.name}] is '
                    f'booted and is in the exclusions list for [{self.name}].'
                )
                return

        if self.pre_dep_boot is not None:
            self.pre_dep_boot(self)

        # make sure all dependencies are booted before booting
        for subsys in self.dependencies:
            if not subsys.booted:
                if boot_dependencies:
                    subsys.boot(boot_dependencies=True)
                else:
                    _logger.warning(
                        f'Cancelling boot request for [{self.name}] because dependency '
                        f'[{subsys.name}] is not booted.'
                    )
                    return

        if self.post_dep_boot is not None:
            self.post_dep_boot(self)
        else:
            self.default_boot()

        self.booted = True
        if Qt_GUI:
            self.booted_sig.emit()
        _logger.info(f'Booted [{self.name}].')

    def shutdown(self, shutdown_dependencies: bool = True, force: bool = False):
        """Shutdown the subsystem.

        Args:
            shutdown_dependencies: If True, shutdown all dependencies after shutting
                down
            force: If True, ignore any exceptions while shutting down.
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
                    f'Cancelling shutdown request for [{self.name}] because subsystem '
                    f'dependent [{subsys.name}] is still booted.'
                )
                return

        try:
            if self.pre_dep_shutdown is not None:
                self.pre_dep_shutdown(self)
            else:
                self.default_shutdown()
        except Exception as exc:
            if not force:
                raise exc

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
                                f'Not shutting down [{subsys.name}] because its '
                                f'dependent [{d.name}] is still booted.'
                            )
                            should_shutdown = False
                    if should_shutdown:
                        subsys.shutdown(shutdown_dependencies=True, force=force)

        try:
            if self.post_dep_shutdown is not None:
                self.post_dep_shutdown(self)
        except Exception as exc:
            if not force:
                raise exc

    def mutual_exclusion(self, sub: Self):
        """Prevent this Subsystem and the given Subsystem from being
        simultaneously booted.

        Args:
            sub: The Subsystem that cannot be booted at the same time as this
                Subsystem.

        """
        self.exclusions.append(sub)
        sub.exclusions.append(self)
