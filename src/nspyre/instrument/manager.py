from typing import Dict

from ..gui import QObject
from .gateway import InstrumentGateway


# insmgr
#   - gateways
#       - inserv1
#           - state_dev (for subs)
#           - state_dev (for user data)
#           - dev1
#           - dev2
#           - mdev -> dev1, dev2, dev3
#       - inserv2
#           - dev3


class _InstrumentManagerDevice:
    def __init__(name: str, gateway: InstrumentGateway):
        """Wrapper for a device residing in an :py:class:`~nspyre.instrument.gateway.InstrumentGateway`.

        Args:
            name: Name of the device on the gateway.
            gateway: :py:class:`~nspyre.instrument.gateway.InstrumentGateway` object containing the device.
        """
        self.__gateway_name__ = name
        self.__gateway__ = gateway

    def __getattr__(self, attr: str):
        """Always re-access the gateway instance in case the gateway reconnected.

        When we access a device from the gateway, it will return an rpyc netref
        object. This creates a problem when the gateway disconnects from the
        instrument server, then later reconnects. If we have a reference to the
        rpyc netref that pointed to the device, it will be stale because it was
        linked to the original gateway. However, if we instead pass around this
        _InstrumentManagerDevice, we can always re-access the gateway device
        whenever we want to access an attribute of the device. This way, if the
        gateway disconnects and reconnects, we will always be accessing the
        attributes of the newly connected gateway, rather than a stale netref.
        """
        return getattr(getattr(self.____gateway__, self.____gateway_name__), attr)

    # TODO might need to implement other dunder methods, e.g.
    # https://github.com/tomerfiliba-org/rpyc/blob/master/rpyc/core/netref.py


class InstrumentManager(QObject):
    def __init__(self, *register_gateway_args, **register_gateway_kwargs):
        """For consolidating connections to multiple instrument gateways. 
        If only connecting to a single :py:class:`~nspyre.instrument.gateway.InstrumentGateway`, 
        you can simply pass the arguments and keyword arguments that you'd 
        normally pass to the gateway here.

        Args:
            register_gateway_args: See arguments for :py:meth:`~nspyre.instrument.manager.InstrumentManager.register_gateway`.
            register_gateway_kwargs: See keyword arguments for :py:meth:`~nspyre.instrument.manager.InstrumentManager.register_gateway`.
        """
        # mapping between a unique device name key and _InstrumentManagerDevice value
        self.devs = {}
        self.register_gateway(*register_gateway_args, **register_gateway_kwargs)

    def register_gateway(
        self,
        *gateway_args,
        default_exclude=False,
        exclude: list[str] = None,
        name_mapping: Dict[str, str] = None,
        **gateway_kwargs,
    ):
        """
        Args:
            gateway_args: See arguments for :py:class:`~nspyre.instrument.gateway.InstrumentGateway`.
            gateway_kwargs: See keyword arguments for :py:class:`~nspyre.instrument.gateway.InstrumentGateway`.
            default_exclude: If True, only add those devices specified in the :code:`name_mapping`.
            exclude: List of device names on the :py:class:`~nspyre.instrument.server.InstrumentServer` \
                that won't be added to the :py:class:`~nspyre.instrument.manager.InstrumentManager`.
            name_mapping: Keys should be the device names on the :py:class:`~nspyre.instrument.server.InstrumentServer` \
                whose values are the corresponding desired name on the :py:class:`~nspyre.instrument.manager.InstrumentManager`. \
                Otherwise their name on the :py:class:`~nspyre.instrument.manager.InstrumentManager` \
                will be the same as that on the :py:class:`~nspyre.instrument.server.InstrumentServer`.
        """
        gw = InstrumentGateway(*args, **kwargs)

        gw_devs = obtain(gw._devs)
        for gw_dev_name in gw_devs:
            if default_exclude and gw_dev_name not in name_mapping:
                continue
            if gw_dev_name not in exclude:
                if gw_dev_name in name_mapping:
                    mgr_dev_name = name_mapping[gw_dev_name]
                else:
                    mgr_dev_name = gw_dev_name

                if mgr_dev_name not in self.devs:
                    self.devs[mgr_dev_name] = _InstrumentManagerDevice(gw_dev_name, gw)
                else:
                    raise ValueError(
                        f'Device named [{mgr_dev_name}] already exists on the InstrumentManager.'
                    )

    def connect(self):
        """Connect to all :py:class:`~nspyre.instrument.gateway.InstrumentGateway`."""
        for gw in self.instrument_gateways:
            gw.connect()

    def disconnect(self):
        """Disconnect from all :py:class:`~nspyre.instrument.gateway.InstrumentGateway`."""
        for gw in self.instrument_gateways:
            gw.disconnect()

    def __getattr__(self, attr: str):
        if attr in self.devs:
            return self.devs[attr]
        else:
            # raise the default python error when an attribute isn't found
            return self.__getattribute__(attr)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()
