.. _instrument_server:

#####################
The Instrument Server
#####################

The instrument server is a tool that allows the user to create a networked server which hosts a collection of instrument drivers. It is basically a wrapper around `rpyc <https://rpyc.readthedocs.io/en/latest/>`__.

You can use the InstrumentServer class to create an instrument server, and add devices to it using the `add` method, which createsan instance of the driver class.

.. code-block:: python

   # inserv.py

   from pathlib import Path

   from nspyre import inserv_cli
   from nspyre import InstrumentServer

   HERE = Path(__file__).parent

   # create a new instrument server
   with InstrumentServer() as inserv:
      # add signal generator driver
      # 'sg' will be an instance of the class 'SigGen' in the file ./drivers/sg.py
      inserv.add('sg', HERE / 'drivers' / 'sg.py', 'SigGen')
      # add data acquisition instrument driver
      # 'daq' will be an instance of the class 'DAQ' in the file ./drivers/daq.py
      inserv.add('daq', HERE / 'drivers' / 'daq.py', 'DAQ')

      # run a CLI (command-line interface) that allows the user to enter
      # commands to control the server
      inserv_cli(inserv)

Once the instrument server has been created, its devices can be accessed using an instrument gateway:

.. code-block:: python

   from nspyre import InstrumentGateway

   # create a new instrument server
   with InstrumentGateway() as gateway:
      gateway.sg.set_amplitude(5)
      gateway.sg.set_frequency(5)

The instrument server is not required, but can be useful in certain situations. Some examples are:

- There is a specific "instrument" computer that controls a critical instrument or set of instruments, but you don't want to run your experiment there. Using an instrument server on the "instrument" computer, you can remotely access its drivers over a network connection, while running your experiment from a different computer.
- You have an instrument that requires significant boot-up / initialization time, or has some sort of inherent state that you don't want to disturb each time you run an experiment. For example, a driver for a motorized stage might require homing each time it boots. However, you don't want to home the stage each time you run an experiment. If you host the stage driver on an instrument server (even on the same machine), you can boot and home the stage once, then use it repeatedly for many experiments without re-homing.

The instrument server can be quite helpful, but it does have some disadvantages. The library that performs the actual network communication is `rpyc <https://rpyc.readthedocs.io/en/latest/>`__. While it does a very good job of making python objects over the network connection act like local python objects, it isn't a perfect abstraction. For many python types, rpyc manipulations will return "netref" objects rather than actual python objects. These netrefs are essentially a reference to an object over the network connection. Sometimes, working with a netref rather than the actual python object can create problems. Luckily, when that happens there is a simple solution: convert the netref to a python object using rpyc's `obtain` method. For example:

.. code-block:: python

   from nspyre import InstrumentGateway
   from rpyc.utils.classic import obtain

   # connect to the instrument server
   with InstrumentGateway() as gateway:
      # let's assume the positions method returns a list object
      # calling it over rpyc causes it to return a netref object
      current_position = gateway.stage.positions()
      # this could fail because some_func doesn't properly utilize duck typing, 
      # and expects a list rather than a netref object
      some_func(current_position)
      # this will work because obtain() converts a netref to a local python 
      # object before passing it to some_func
      some_func(obtain(current_position))
