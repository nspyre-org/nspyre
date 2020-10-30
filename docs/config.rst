######################
Configuration Settings
######################

NSpyre uses configuration files to understand what hardware you're connecting, which spyrelets you want to access, their
parameters and required hardware, and how to configure connections to MongoDB and Instrument Servers. In order to run, nspyre needs to
be given two configuration files - one for the instrument server and one for spyreThere is a convenient
command-line interface to make providing file paths and switching between configurations easy.

CLI
===

Add the configuration file for your experiment:

.. code-block:: console

   $ nspyre-config client -a path/to/client_config.yaml
   $ nspyre-config -l
   * 0: client_default_config.yaml
     1: path/to/client_config.yaml

Set the activate configuration file to your experiment configuration:

.. code-block:: console

   $ nspyre-config client -s 1
   $ nspyre-config client -l
     0: client_default_config.yaml
   * 1: path/to/client_config.yaml

Delete a configuration file from path:

.. code-block:: console

   $ nspyre-config client -d 2
   $ nspyre-config client -l
   * 0: client_default_config.yaml

And if you completely f**k'd your system, you can get a restore the default configuration of either or both files:

.. code-block:: console

   $ nspyre-config reset inserv
   $ nspyre-config inserv -l

   $ nspyre-config reset spyre
   $ nspyre-config spyre -l

   $ nspyre-config reset
   $ nspyre-config -l


Configuration Files
===================

There are two sets of configuration files in nspyre. One is for the instrument 
server, and one for the spyrelets and other tools connecting to the instrument 
server. These are referred to as the "server" and "client", respectively. The config files used by the client and server can be modified using the ``nspyre-config`` tool. Details about its operation can be found by typing 
``nspyre-config --help``, but some usage examples are shown below.

Adding Config Files
-------------------
To add a new client config file, use the command:

.. code-block:: console
   
   > nspyre-config client -a path/to/client_config.yaml
   >

And a server config:

.. code-block:: console
   
   > nspyre-config server -a path/to/server_config.yaml
   >

The paths are allowed to be relative to the current working directory.

Listing Configs Files
---------------------
The console command below lists the set of config files that the client collects its configuration entries from:

.. code-block:: console

   > nspyre-config client -l
   0: client_default_config.yaml
   1: /path/to/client_config.yaml
   >

Removing Config Files
---------------------
To remove a config file, use the ``-d`` option, then the path of the config file to remove:

.. code-block:: console

   > nspyre-config client -l
   0: client_default_config.yaml
   1: /path/to/client_config.yaml
   > nspyre-config client -d path/to/client_config.yaml
   > nspyre-config client -l  
   0: client_default_config.yaml
   >

Or they can be deleted by entry number e.g.:

.. code-block:: console

   > nspyre-config client -l
   0: client_default_config.yaml
   1: /path/to/client_config.yaml
   > nspyre-config -d 1
   > nspyre-config client -l  
   0: client_default_config.yaml
   >

Configuration Entries
=====================

The client and server each have a separate set of configuration entries that they expect to be contained somewhere in their list of config files. The configuration entries may be all in a single file, or split into multiple if desired. However, if multiple top-level entries of the same name exist, the one from the last-read config file will take precedence. The config files are read in the same order as they are listed with ``nspyre-config -e``.

The config entries for the client and server are listed and documented below with example config files.



Example Configurations
======================

These are the default configuration files with which nspyre comes loaded.

Inserv Config File
------------------

.. code-block:: yaml

   server_settings:
     # name of the instrument server that the client will use to connect
     name: 'local1'
     # ip address / domain name of the instrument server as seen by the client
     # recommended to use a local network static ip for remote clients, e.g.:
     # ip: '192.168.0.15'
     ip: 'localhost' # only allow client connections from the same machine
     # port to run the RPyC instrument server on
     port: 5556

   # address of the mongodb server in the format 'mongodb://<ip>:<port>/'
   mongodb_addr: 'mongodb://localhost:27017/'

   # the devices entry will be used by the instrument server to automatically load
   # the specified devices on startup - the syntax is:
   devices_doc: # 'devices' for the real one
     device_name1:
       # lantz class specified as a path in the style of a python import starting
       # from the lantz-drivers folder,
       # e.g. 'examples.LantzSignalGenerator' or 'examples.dummydrivers.DummyOsci'
       lantz_class: 'lantz driver'
       # instead of 'lantz_class', can also be specified by 'class' / 'class_file'
       class: 'python class name' # e.g. 'LantzSignalGenerator'
       # python file containing the class above (can be absolute or relative to
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

     my_exp:
       file: '../spyrelet/examples/test_spyrelets.py'
       class: 'MyExperiment'
       device_aliases:
         sg: 'local1/fake_tcpip_sg'
         osc: 'local1/fake_osc'
       spyrelets: {s2: 's2'}
       args: {}
