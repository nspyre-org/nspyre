"""
Related to patching pint to work with npsyre

Copyright (c) 2021, Michael Solomon, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""

from pint import get_application_registry
import rpyc

# create a pint registry universal to nspyre
ureg = get_application_registry()
Q_ = ureg.Quantity

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
