.. attention::
   
   We know some of these webpages could use some work -- this documentation has only recently been created and is in active development. It is updated regularly, so check back weekly.

***************
Getting Started
***************

Testing Successful Installation
-------------------------------

The first thing you should do is test that the installation was successful. This will also get you familiar with the startup process
for running NSpyre on new systems. Fortunately, NSpyre and Lantz come bundled with default configurations that allow you to test your
installation out of the box.

Lantz comes bundled with a live simulation signal generator that runs over a TCP connection and is can be useful to check
everything is running correctly. As with any experiment, you have to make sure all your hardware is on and connected before
starting the instrument server (there are now methods for loading devices into the server without a hard reset but we'll
get to those later). Therefore, start the simulated device in a new console (remember to activate your conda env):

.. code-block:: console

   $ lantz-sims fungen tcp
   Dispatching fungen
   2020-15-10 02:36:34 Listening to localhost:5678
   2020-15-10 02:36:34 interrupt the program with Ctrl-C

The test signal generator is now successfully started and ready to be connected to the instrument server.

The first thing you have to do on a new startup of nspyre is make sure that the MongoDB database is running. Open a new console (leave the other
running) and use the CLI for configuring nspyre's database:

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

The CLI will print out logging information as it runs, but if the MongoDB process has started successfully and the databases
are running, then the output will end in the above printout.

Next, it's time to start the instrument server. This is a RPyC service which handles the connections to each device and functions
as a server for communicating between nspyre experiment code and your hardware. If the MongoDB databases are not running, then
the instrument server will error out on startup. To start the server simply type:

.. code-block:: console

   $ nspyre
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

Depending on the logging level set, the instrument server will printout lots of information about the state of the server
as it attempts to startup, establish connections, and load the hardware specified in your configuration file. If the
instrument server has successfully started and loaded all specified devices, then at a minimum you will see the above
information. Notice that there is a new prompt `inserv >` -- this is the instrument server command line and can be very
useful for quickly reloading devices, debugging, and checking the start of the system. To see all the available commands simply
type help:

.. code-block:: console

   inserv > help

   Documented commands (type help <topic>):
   ========================================
   config  dev      help  quit     server_restart  server_stop
   debug   dev_all  list  restart  server_start

   inserv >

*Note:* This console should be kept running at all times, it is the master process for the instrument server. If you close this
console the server process will shutdown and disconnect. In addition to being something you obviously don't want to do while running
nspyre, keeping the console window in the corner of your screen is very useful for checking the logging commands for
successful completion of communications with hardware with operating.

Finally, if you want to boot up the UI and run a simple measurement, open a new console window and use:

.. code-block:: console

   $ nspyre

From here you can start the instrument manager and launch spyrelets. Both use a Gateway to connect to the instrument server and is
the standard method of connecting and communicating with the instrument server. Note that for some users the instrument manager may
be faulty, but the GUI is currently being completely rewritten and should be available soon.

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

Full documentation for LANTZ is available at https://lantz.readthedocs.io/en/0.3/.
The basic layer on which NSpyere is based is called LANTZ. This framework is used to control and connect to instruments with different connectivities (server, ethernet, usb, etc.). Lantz contains drivers that create 3 types of attributes for each driver:

* Feature (Feat), which is a readonly or a read/write variable (e.g, the frequency of a signal generator, which you can both read and set).
* Dictionary feature (dicFeat), which works the same as @Feat, but is a dictionary of such Feats.
    
    - This is useful for instrument with several of the control or ability (i.e. a counting card with multiple channels)

* Action, which is a function that acts on the device (calibration, initialization, get an array of points, etc.)
    
    - In general, when it is a single variable that is easy to read or read/write that should be a @Feat. When it is more complicated it is usually an @Action.

In each driver file there will be imported libraries. The minimum you need is to import the driver and the attributes (Action, Feat, DicFeat, ureg), but other standardized libraries like numpy can also be imported. An example of a driver can be found in your lantz folder, in the ``drivers/`` subdirectory. Opening stanford/sg396 in your editor would show the driver for the signal generator.

The lantz docs linked above provide a very good introduction of a toy signal generator to so a typical use case.


