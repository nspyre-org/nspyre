.. attention::
   
   We know some of these webpages could use some work -- this documentation is in active development. If you discover any errors or inconsistencies, please report them at `GitHub <https://github.com/nspyre-org/nspyre/issues>`__.

###############
Getting Started
###############

Testing Successful Installation
===============================

The first thing you should do is test that the installation was successful. This will also get you familiar with the startup process
for running NSpyre on new systems. Fortunately, NSpyre comes bundled with default configurations that allow you to test your
installation out of the box.

Lantz comes bundled with a live simulation signal generator that runs over a TCP/IP connection and can be useful to check
everything is running correctly. As with any experiment, you have to make sure all your hardware is on and connected before
starting the instrument server (there are now methods for loading devices into the server without a hard reset but we'll
get to those later). Therefore, start the Lantz simulated function generator in a new console (remember to activate your conda env):

.. code-block:: bash

   ([nspyre-env]) $ lantz-sims fungen tcp
   Dispatching fungen
   2020-15-10 02:36:34 Listening to localhost:5678
   2020-15-10 02:36:34 interrupt the program with Ctrl-C

The test signal generator is now successfully started and ready to be connected to the instrument server.

The first thing you have to do on a new startup of nspyre is make sure that the MongoDB database is running. Open a new console (leave the other
running) and use the CLI for starting nspyre's database:

.. code-block:: bash

   ([nspyre-env]) $ nspyre-mongodb
   ...
   Implicit session: session { "id" : UUID("70838660-1424-4f33-b0b0-493f3b5022d1") }
   MongoDB server version: 4.2.10
   {
	   "ok" : 1,
	   "$clusterTime" : {
		   "clusterTime" : Timestamp(1602747679, 1),
		   "signature" : {
			   "hash" : BinData(0,"AAAAAAAAAAAAAAAAAAAAAAAAAAA="),
			   "keyId" : NumberLong(0)
		   }
	   },
	   "operationTime" : Timestamp(1602747679, 1)
   }

The CLI will print out logging information as it runs, but if the MongoDB process has started successfully and the database
is running, then the output will end in a printout similar to the one above.

Next, it's time to start the instrument server. This is a `RPyC <https://rpyc.readthedocs.io/en/latest/index.html>`__ service which handles the connections to each device and functions
as a server for communicating between nspyre experiment code and your hardware. If the MongoDB databases are not running, then
the instrument server will error out on startup. To start the server simply type:

.. code-block:: bash

   ([nspyre-env]) $ nspyre-inserv
   2020-10-15 02:37:55,888 -- INFO -- starting instrument server...
   2020-10-15 02:37:55,894 -- INFO -- loaded config files ['path/to/inserv_config.yaml']
   2020-10-15 02:37:55,895 -- INFO -- connecting to mongodb server [mongodb://localhost:27017/]...
   2020-10-15 02:37:55,950 -- INFO -- connected to mongodb server [mongodb://localhost:27017/]
   2020-10-15 02:37:55,950 -- INFO -- starting RPyC server...
   2020-10-15 02:37:55,951 -- INFO -- server started on [0.0.0.0]:5556
   ...
   2020-10-15 02:37:56,438 -- INFO -- reloaded all devices
   instrument server started...
   inserv >

Depending on the logging level set, the instrument server will print out lots of information about the state of the server
as it attempts to startup, establish connections, and load the hardware specified in your configuration file. If the
instrument server has successfully started and loaded all specified devices, then at a minimum you will see the above
information. Notice that there is a new prompt `inserv >` - this is the instrument server command line and can be very
useful for quickly reloading devices, debugging, and checking the state of the system. To see all the available commands simply
type help:

.. code-block:: bash

   inserv > help

   Documented commands (type help <topic>):
   ========================================
   config  dev      help  quit     server_restart  server_stop
   debug   dev_all  list  restart  server_start

   inserv >

.. important::

   This console should be kept running at all times, as it is the master process for the instrument server. If you close this
   console the server will shutdown, disconnecting any running devices in the process.

.. tip::

   Keeping the console window in the corner of your screen while operating is very useful for verifying successful
   completion of communications with hardware.

Finally, if you want to boot up the graphical user interface, open a new console window and run:

.. code-block:: bash

   $ nspyre

From here you can start the instrument manager (for manually controlling instrument settings), launch spyrelets (for running
experiments), and view data (for plotting data from spyrelets). These functionalities use a *Gateway* to connect to the instrument
server and is the standard method of connecting and communicating with the instrument server. For users running nspyre through
a jupyter notebook, or an interpreter this is the desired method.

Next Steps
----------

TODO

Lantz
-----

`Lantz <https://lantz.readthedocs.io/en/0.3/>`__ is a framework for writing drivers to control and connect to instruments that is used extensively with nspyre. Lantz drivers can have 3 types of attributes:

* Feature (Feat), which can be a read only, or a read/write parameter (e.g. the frequency of a signal generator).
* Dictionary feature (dictFeat), which is essentially a dictionary of Feats. This is useful for instruments with several parameters
  that all function identically (e.g. the digital inputs/outputs of a data acquisition system)
* Action, which is a function that acts on the device (e.g. calibration, initialization, get an array of points, etc.)

In general, when the device property is a single variable that is easy to read or read/write that should be a Feat. When it
is more complicated it is usually an Action. In each driver file there will be imported libraries. The minimum set of classes you need
to import from lantz are the driver class (e.g. *Driver*, *LibraryDriver*, *MessagedBasedDriver*) corresponding to the type of device
you are implementing and the attributes classes (i.e. *Feat*, *DicFeat*, *Action*, *ureg*).

Lantz comes bundled with a large selection of drivers, which can be used by importing the associated class from ``lantz.drivers`` and
can be found in the `lantz-drivers <https://github.com/lantzproject/lantz-drivers/tree/master/lantz/drivers>`__ repo or in the
*drivers* subpackage of lantz. For example, opening ``lantz/drivers/stanford/sg396.py`` in your editor would show the driver for an
actual signal generator (the SG396) while opening ``lantz/drivers/examples/fungen.py`` would show the driver for the simulated device.

The lantz docs linked `above <https://lantz.readthedocs.io/en/0.3/>`__ provide a very good introduction starting from a toy signal
generator and working up to a typical use case.
