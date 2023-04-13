from typing import Dict

from .gateway import InstrumentGateway
from .gateway import InstrumentGatewayDevice


class InstrumentManager:
    def __init__(
        self, *register_gateway_args, register_gateway=True, **register_gateway_kwargs
    ):
        """For consolidating connections to multiple instrument gateways.
        If only connecting to a single :py:class:`~nspyre.instrument.gateway.InstrumentGateway`,
        you can simply pass the arguments and keyword arguments that you'd
        normally pass to the gateway here.

        Args:
            register_gateway_args: See arguments for :py:meth:`~nspyre.instrument.manager.InstrumentManager.register_gateway`.
            register_gateway: if True, call :py:meth:`~nspyre.instrument.manager.InstrumentManager.register_gateway`.
            register_gateway_kwargs: See keyword arguments for :py:meth:`~nspyre.instrument.manager.InstrumentManager.register_gateway`.
        """
        # mapping between a unique device name key and InstrumentGatewayDevice value
        self.devs = {}
        # list of InstrumentGateway
        self.gateways = []
        if register_gateway:
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
        gw = InstrumentGateway(*gateway_args, **gateway_kwargs)
        gw.connect()

        if name_mapping is None:
            name_mapping = {}
        if exclude is None:
            exclude = []

        for gw_dev_name in gw._devs:
            if default_exclude and gw_dev_name not in name_mapping:
                continue
            if gw_dev_name not in exclude:
                if gw_dev_name in name_mapping:
                    mgr_dev_name = name_mapping[gw_dev_name]
                else:
                    mgr_dev_name = gw_dev_name

                if mgr_dev_name not in self.devs:
                    self.devs[mgr_dev_name] = InstrumentGatewayDevice(gw_dev_name, gw)
                else:
                    raise ValueError(
                        f'Device named [{mgr_dev_name}] already exists on the InstrumentManager.'
                    )

        self.gateways.append(gw)

    def disconnect(self):
        """Disconnect from all :py:class:`~nspyre.instrument.gateway.InstrumentGateway`."""
        for gw in self.gateways:
            gw.disconnect()

    def __getattr__(self, attr: str):
        if attr in self.devs:
            return self.devs[attr]
        else:
            # raise the default python error when an attribute isn't found
            return self.__getattribute__(attr)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.disconnect()
