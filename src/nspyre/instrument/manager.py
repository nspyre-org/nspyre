from typing import Dict
from typing import Optional

from .gateway import InstrumentGateway
from .gateway import InstrumentGatewayDevice


class InstrumentManager:
    def __init__(
        self,
        *register_gateway_args,
        register_gateway: bool = True,
        auto_device_discovery: bool = True,
        **register_gateway_kwargs,
    ):
        """For consolidating connections to multiple instrument gateways.
        If only connecting to a single
        :py:class:`~nspyre.instrument.gateway.InstrumentGateway`, you can simply pass
        the arguments and keyword arguments that you'd normally pass to the gateway
        here. The :py:class:`~nspyre.instrument.manager.InstrumentManager`
        returns an :py:class:`~nspyre.instrument.manager.InstrumentManagerDevice`
        when a device attribute is accessed, e.g.:

        .. code-block:: python

            from nspyre import InstrumentManager

            with InstrumentManager() as mgr:
                # let's assume "dev1" was created on the instrument server as an
                # instance of "MyDriver"

                # d is an InstrumentManagerDevice object
                d = mgr.dev1
                # run the get_something() method of dev1 and print its return value
                print(d.get_something())
                print(isinstance(mgr.dev1, MyDriver)) # False
                print(isinstance(mgr.dev1, InstrumentManagerDevice)) # True

        Args:
            register_gateway_args: See arguments for
                :py:meth:`~nspyre.instrument.manager.InstrumentManager.register_gateway`.
            register_gateway: if True, call
                :py:meth:`~nspyre.instrument.manager.InstrumentManager.register_gateway`.
            auto_device_discovery: if True, when an attribute of the manager is
                accessed, but the device hasn't been registered yet with the
                manager using
                :py:meth:`~nspyre.instrument.manager.InstrumentManager.register_device`,
                the device will be automatically registered.
            register_gateway_kwargs: See keyword arguments for
                :py:meth:`~nspyre.instrument.manager.InstrumentManager.register_gateway`.
        """
        # see InstrumentManagerDevice
        self.auto_device_discovery = auto_device_discovery
        # mapping between a unique device name key and InstrumentGatewayDevice value
        self.devs: Dict[str, InstrumentGatewayDevice] = {}
        # list of InstrumentGateway
        self.gateways: list[InstrumentGateway] = []
        if register_gateway:
            self.register_gateway(*register_gateway_args, **register_gateway_kwargs)

    def register_gateway(
        self,
        *gateway_args,
        default_exclude: bool = False,
        exclude: Optional[list[str]] = None,
        name_mapping: Optional[Dict[str, str]] = None,
        **gateway_kwargs,
    ):
        """Create and connect to an `~nspyre.instrument.gateway.InstrumentGateway`,
        associate it with this :py:class:`~nspyre.instrument.manager.InstrumentManager`,
        and add all of its devices to this
        :py:class:`~nspyre.instrument.manager.InstrumentManager`.

        Args:
            gateway_args: See arguments for
                :py:class:`~nspyre.instrument.gateway.InstrumentGateway`.
            gateway_kwargs: See keyword arguments for
                :py:class:`~nspyre.instrument.gateway.InstrumentGateway`.
            default_exclude: If True, only add those devices specified in the
                :code:`name_mapping`.
            exclude: List of device names on the
                :py:class:`~nspyre.instrument.server.InstrumentServer` that won't be
                added to the :py:class:`~nspyre.instrument.manager.InstrumentManager`.
            name_mapping: Keys should be the device names on the
                :py:class:`~nspyre.instrument.server.InstrumentServer` whose values are
                the corresponding desired name on the
                :py:class:`~nspyre.instrument.manager.InstrumentManager`. Otherwise
                their name on the
                :py:class:`~nspyre.instrument.manager.InstrumentManager` will be the
                same as that on the
                :py:class:`~nspyre.instrument.server.InstrumentServer`.
        """
        gw = InstrumentGateway(*gateway_args, **gateway_kwargs)
        gw.connect()

        if name_mapping is None:
            name_mapping = {}
        if exclude is None:
            exclude = []

        self.gateways.append(gw)

        for gw_dev_name in gw._devs:
            if default_exclude and gw_dev_name not in name_mapping:
                continue
            if gw_dev_name not in exclude:
                if gw_dev_name in name_mapping:
                    mgr_dev_name = name_mapping[gw_dev_name]
                else:
                    mgr_dev_name = gw_dev_name
                self.register_device(getattr(gw, gw_dev_name), name=mgr_dev_name)

    def register_device(self, dev: InstrumentGatewayDevice, name: Optional[str] = None):
        """Add a device to the :py:class:`~nspyre.instrument.manager.InstrumentManager`.

        Args:
            dev: The device to add.
            name: The name of the device on the
                :py:class:`~nspyre.instrument.manager.InstrumentManager`. If
                :code:`None`, the
                :py:class:`~nspyre.instrument.gateway.InstrumentGatewayDevice`
                name will be used.
        """
        if name is None:
            name = dev.____gateway_dev_name__

        if name not in self.devs:
            self.devs[name] = dev
        else:
            raise ValueError(
                f'Device named [{name}] already exists on the ' 'InstrumentManager.'
            )

    def disconnect(self):
        """Disconnect from all
        :py:class:`~nspyre.instrument.gateway.InstrumentGateway`."""
        for gw in self.gateways:
            gw.disconnect()

    def __getattr__(self, attr: str):
        return InstrumentManagerDevice(attr, self)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.disconnect()


class InstrumentManagerDevice:
    def __init__(self, name: str, manager: InstrumentManager):
        """Wrapper for a device residing in an \
        :py:class:`~nspyre.instrument.manager.InstrumentManager`.
        Performs similar a function as an
        :py:class:`~nspyre.instrument.gateway.InstrumentGatewayDevice`. See
        those docs for details.

        Args:
            name: Name of the device on the gateway.
            gateway: :py:class:`~nspyre.instrument.gateway.InstrumentGateway` object
                containing the device.
        """
        self.____manager_dev_name__ = name
        self.____manager__ = manager

    def __getattr__(self, attr: str):
        if self.____manager_dev_name__ not in self.____manager__.devs:
            # the device hasn't been registered yet with the manager
            found_dev = None
            if self.____manager__.auto_device_discovery:
                # try searching in the gateways for a device of that name
                for gw in self.____manager__.gateways:
                    if hasattr(gw, self.____manager_dev_name__):
                        found_dev = getattr(gw, self.____manager_dev_name__)
                        break

            if found_dev is not None:
                self.____manager__.register_device(found_dev)
            else:
                raise ValueError(
                    f'InstrumentManager [{self.____manager__}] '
                    f'does not contain a device named [{self.____manager_dev_name__}].'
                )

        gw_dev = self.____manager__.devs[self.____manager_dev_name__]
        if attr == 'device':
            return gw_dev.device
        else:
            return getattr(gw_dev, attr)
