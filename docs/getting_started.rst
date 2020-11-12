.. attention::
   
   We know some of these webpages could use some work -- this documentation is in active development. If you discover any errors or inconsistencies, please report them on `GitHub <https://github.com/nspyre-org/nspyre/issues>`_.

***************
Getting Started
***************

Testing Successful Installation
-------------------------------

The first thing you should do is test that the installation was successful. This will also get you familiar with the startup process
for running NSpyre on new systems. Fortunately, NSpyre comes bundled with default configurations that allow you to test your
installation out of the box.

Lantz comes bundled with a live simulation signal generator that runs over a TCP/IP connection and can be useful to check
everything is running correctly. As with any experiment, you have to make sure all your hardware is on and connected before
starting the instrument server. Start the lantz simulated function generator device in a new console (remember to activate your conda env) with:

.. code-block:: console

   $ lantz-sims fungen tcp
   Dispatching fungen
   2020-15-10 02:36:34 Listening to localhost:5678
   2020-15-10 02:36:34 interrupt the program with Ctrl-C

The test signal generator is now successfully started and ready to be connected to the instrument server.

The first thing you have to do on a new startup of nspyre is make sure that the MongoDB database is running. Open a new console (leave the other
running) and use the CLI for starting nspyre's database:

.. code-block:: console

   $ nspyre-mongodb
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
is running, then the output will end in the above printout.

Next, it's time to start the instrument server. This is a `RPyC <https://rpyc.readthedocs.io/en/latest/index.html>`_ service which handles the connections to each device and functions
as a server for communicating between nspyre experiment code and your hardware. To start the server simply type:

.. code-block:: console

   $ nspyre-inserv
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
useful for quickly reloading devices and debugging. To see all the available commands simply
type help:

.. code-block:: console

   inserv > help

   Documented commands (type help <topic>):
   ========================================
   config  dev      help  quit     server_restart  server_stop
   debug   dev_all  list  restart  server_start

   inserv >

*Note:* This console should be kept running at all times, as it is the master process for the instrument server. If you close this
console the server will shutdown. Keeping the console window in the corner of your screen is very useful for verifying
successful completion of communications with hardware.

Finally, if you want to boot up the graphical user interface, open a new console window and run:

.. code-block:: console

   $ nspyre

From here you can start the instrument manager (for manually controlling instrument settings), spyrelet launcher (for running experiments), and data viewer (for plotting data from spyrelets).

Next Steps
----------

If you've made it here, then nspyre is successfully running on your machine and you can begin using nspyre for your
own experiments. The first thing you need to do is write configuration files for the instrument server and spyrelets, so
that nspyre knows what you want to run. The instrument server config file contains information on what connections to make (for
mongoDB and it's out ports), and what hardware should be loaded (with what parameters). The spyrelet config files specify
the experimentation code files you plan to run and the associated hardware loaded in the inserv config file needed. More
information about these configuration files, how to set them, and examples are included in the Configuration Section of the
docs.

Lantz
-----

`Lantz <https://lantz.readthedocs.io/en/0.3/>`_ is a framework for writing drivers to control and connect to instruments that is used extensively with nspyre.
Lantz drivers can have 3 types of attributes:

* Feature (Feat), which can be a read only, or a read/write parameter of the instruments (e.g, the frequency of a signal generator).
* Dictionary feature (dictFeat), which is essentially a dictionary of Feats. This is useful for instruments with several parameters that all function identically, like the digital inputs/outputs of a data acquisition system
* Action, which is a function that acts on the device (calibration, initialization, get an array of points, etc.)

The code for all of the drivers built in to lantz can be found `here <https://github.com/lantzproject/lantz-drivers/tree/master/lantz/drivers>`_

The lantz docs linked above provide a very good introduction of a toy signal generator to a typical use case.


