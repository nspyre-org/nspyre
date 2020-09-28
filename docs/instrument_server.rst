.. attention::
   
   We know some of these webpages could use some work -- this documentation has only recently been created and is in active development. It is updated regularly, so check back weekly.

#####################
The Instrument Server
#####################

The Instrument Server (inserv for short) connects to and controls all of the physical devices used for an experiment, then creates a server interface that can be connected to from local, or remote programs over a TCP/IP network connection. More specifically, it uses a remote procedure call system (`RPyC`_) to allow clients to manipulate python objects (like instrument drivers) as if they existed on the client machine.

.. _RPyC: https://rpyc.readthedocs.io/en/latest/

The inserv can be started using the ``nspyre-inserv`` command. Details about its operation can be found by typing ``nspyre-inserv --help``. On startup, the server will attempt connection to the MongoDB database, as well as all of the instruments specified in it's config file. Once it has successfully started, the inserv will serve a shell prompt:
   
.. code-block:: console
   
   inserv > 

This shell prompt allows runtime control of the instrument server. The server can be started (``server_start``) and stopped (``server_stop``), the config file reloaded (``config``), and individual devices can be reloaded (``dev``). For a list of all available commands, type ``help``, or for documentation on specific commands type ``help <command>`` e.g.

.. code-block:: console
   
   inserv > help

   Documented commands (type help <topic>):
   ========================================
   config  dev      help  quit     server_restart  server_stop
   debug   dev_all  list  restart  server_start  

   inserv > help dev
   Restart the connection with a device
   <string> the device name
   inserv > 
