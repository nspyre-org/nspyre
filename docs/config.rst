######################
Configuration Settings
######################

NSpyre uses configuration files to understand what hardware you're connecting, which spyrelets you want to access, their
parameters and required hardware, and how to configure connections to MongoDB and Instrument Servers. In order to run, nspyre needs to
be given two configuration files - one for the instrument server and one for *'spyre'* (i.e. the client). There is a convenient
command-line interface to make providing file paths and switching between configurations easy.

Command-line Interface (CLI)
============================
The config files used by the client and instrument server can be changed using the ``nspyre-config`` tool. Details about its operation
can be found by typing ``nspyre-config --help``, but some usage examples are shown below.

Add the configuration file for your experiment:

.. code-block:: console

   $ nspyre-config client -a path/to/client_config.yaml
   $ nspyre-config -l
   * 0: client_default_config.yaml
     1: path/to/client_config.yaml

Set the activate configuration file to your experiment configuration:

.. code-block:: console

   $ nspyre-config client -s 1  # (or using path/to/client_config.yaml)
   $ nspyre-config client -l
     0: client_default_config.yaml
   * 1: path/to/client_config.yaml

Delete a configuration file from path:

.. code-block:: console

   $ nspyre-config client -d 2  # (or using path/to/client_config.yaml)
   $ nspyre-config client -l
   * 0: client_default_config.yaml

..
   Factory Reset
   -------------
..
   And if you completely f**k'd your system, you can restore the default configuration of either or both files:
..
   .. code-block:: console
..
      $ nspyre-config reset inserv
      $ nspyre-config inserv -l
      * 0: server_default_config.yaml
..
      $ nspyre-config reset client
      $ nspyre-config client -l
      * 0: client_default_config.yaml
..
      $ nspyre-config reset
      $ nspyre-config -l
      inserv:
      * 0: server_default_config.yaml
      client
      * 0: client_default_config.yaml

Configuration Entries
=====================

The client and inserv each have a separate set of configuration entries that they expect to be contained somewhere in their
respective config files. The configuration entries for the client and server are documented below with the default configurations
presented as an example.

.. _`Configuration Section`:

Example Configurations
======================

These are the default configuration files with which NSpyre comes loaded. They can be used as starting points for your own
custom configuration files.

Inserv Config File
------------------

.. code-block:: yaml

   server_settings:
     # name of the instrument server that the client will use to connect
     name: 'local1'
     # ip address / domain name of the instrument server as seen by the client
     # recommended to use a local network static ip for remote clients, e.g.:
     # ip: '192.168.0.15'
     # 'localhost' can be used to only allow client connections from the same machine
     ip: 'localhost'
     # port to run the RPyC instrument server on
     port: 5556

   # address of the mongodb server in the format 'mongodb://<ip>:<port>/'
   # this generally shouldn't change
   mongodb_addr: 'mongodb://localhost:27017/'

   # the devices entry will be used by the instrument server to automatically load
   # the specified devices on startup - the syntax is:
   devices_documentation: # 'devices' for the real one
     # user-supplied alias for the device on the instrument server
     device_name1:
       # lantz class specified as a path in the style of a python import starting
       # from the lantz-drivers folder,
       # e.g. 'examples.LantzSignalGenerator' or 'examples.dummydrivers.DummyOsci'
       # see https://github.com/lantzproject/lantz-drivers/tree/master/lantz/drivers
       lantz_class: 'lantz driver'
       
       # if the driver is not part of lantz-drivers, it can be specified by an
       # ordinary python class stored somewhere on the file system by using the 
       # 'class' and 'class_file' parameters - in this case 'lantz_class' 
       # should be omitted
       class: 'python class name' # e.g. 'LantzSignalGenerator'
       # python file containing the class (can be absolute or relative to
       # this config file), e.g. class_file: '../path/to/driver/fungen.py'
       class_file: 'file path'
       
       # list of arguments to be passed to the constructor for the driver
       args: ['arg1', 'arg2', 'arg3']
       # list of keyword arguments to be passed to the constructor for the driver
       kwargs:
         key1: 'value1'
         key2: 'value2'
     device_name2:
       # etc...

   # actual devices
   devices:
     fake_tcpip_sg:
       lantz_class: examples.LantzSignalGenerator
       args: [TCPIP::localhost::5678::SOCKET]
       kwargs: {}
     fake_sg:
       lantz_class: examples.dummydrivers.DummyFunGen
       args: []
       kwargs: {}
     fake_osc:
       lantz_class: examples.dummydrivers.DummyOsci
       args: []
       kwargs: {}
     fake_shutter:
       lantz_class: examples.dummydrivers.DummyShutter
       args: []
       kwargs: {}

Spyre Config File
-----------------

.. code-block:: yaml

   # address of the mongodb server
   mongodb_addr: 'mongodb://localhost:27017/'

   # experiment (spyrelets) list - the syntax is:
   # name:
   #   file: 'path/to/file.py' (can be absolute or relative to this config)
   #   class: 'SpyreletClass'
   #   device_aliases: {sg1: 'local_inserv1/fake_sg',
   #                   osc1: 'local_inserv1/fake_osc'} }
   #   [optional] spyrelets: {'sub1': 'sub_spyrelet1', ...}
   #   [optional] args: 'Other arguments'
   spyrelets:
     s2:
       file: '../spyrelet/examples/test_spyrelets.py'
       class: 'SubSpyrelet'
       device_aliases: {sg: 'local1/fake_tcpip_sg'}
       spyrelets: {}
       args: {}

     my_exp:
       file: '../spyrelet/examples/test_spyrelets.py'
       class: 'MyExperiment'
       device_aliases:
         sg: 'local1/fake_tcpip_sg'
         osc: 'local1/fake_osc'
       spyrelets: {s2: 's2'}
       args: {}
