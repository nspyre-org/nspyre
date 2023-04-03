import logging

# from ..misc.misc import QObject
# from ..misc.misc import Qt_GUI


_logger = logging.getLogger(__name__)


class Subsystem(QObject):
    """Generalized experimental subsystem that allows for management of
    dependencies between subsystems for boot sequencing."""

    if gui:
        # for when the subsystem is booted / shutdown
        state_changed = QtCore.Signal(bool)

    def __init__(
        self,
        name,
        pre_boot_fun=None,
        boot_fun=None,
        shutdown_fun=None,
        dependencies=None,
    ):
        """
        Args:
            name: subsystem name
            pre_boot_fun: function to run before booting any dependency subsystems; should take 1 argument, which is the subsystem object
            boot_fun: function to run to boot the subsystem; should take 1 argument, which is the subsystem object
            shutdown_fun: function to run to shutdown the subsystem; should take 1 argument, which is the subsystem object
            dependencies: list of Subsystem objects this subsystem depends on; they will be booted (in order) before this subsystem, and shutdown (in reverse order) after this subsystem shuts down
        """
        super().__init__()

        # subsystem name
        self.name = name
        # driver objects associated with the subsytem
        self.drivers = {}

        # dependency subsystem
        if dependencies is not None:
            self.dependencies = dependencies
        else:
            self.dependencies = []

        # dependent subsystems
        self.dependents = []
        if dependencies is not None:
            # set self as a dependent for all dependencies
            for subsys in self.dependencies:
                subsys.dependents.append(self)

        self.pre_boot_fun = pre_boot_fun
        self.boot_fun = boot_fun
        self.shutdown_fun = shutdown_fun
        self.booted = False

    def __str__(self):
        return f'{self.name} booted: {self.booted}'

    def pre_dep_boot(self):
        """Run once boot is requested, before booting any dependencies.
        Subclasses may override this"""
        pass

    def post_dep_boot(self):
        """Run once boot is requested, after booting any dependencies.
        Subclasses may override this"""
        pass

    def boot(self, boot_dependencies=True):
        if self.booted:
            _logger.warning(
                f'Ignoring boot request for [{self.name}] because it is already booted.'
            )
            return
        _logger.info(f'Booting [{self.name}]...')

        if self.pre_boot_fun is not None:
            self.pre_boot_fun(self)

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

        if self.boot_fun is not None:
            self.boot_fun(self)

        self.booted = True
        self.state_changed.emit(self.booted)
        _logger.info(f'Booted [{self.name}].')

    def pre_dep_shutdown(self):
        """Run once shutdown is requested, but before shutting down any dependencies.
        Subclasses may override this"""
        pass

    def shutdown(self, shutdown_dependencies=True):
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

        if self.shutdown_fun is not None:
            self.shutdown_fun(self)

        # remove all driver objects
        for d in self.drivers:
            self.drivers[d] = None

        self.booted = False
        self.state_changed.emit(self.booted)
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

    def __getattr__(self, attr: str):
        if attr in self.drivers:
            return self.drivers[attr]
        else:
            # raise the default python error when an attribute isn't found
            return self.__getattribute__(attr)
