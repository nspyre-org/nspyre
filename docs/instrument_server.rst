.. attention::
   
   We know some of these webpages could use some work -- this documentation has only recently been created and is in active development. It is updated regularly, so check back weekly.

#####################
The Instrument Server
#####################

The Instrument Server is where the lantz driver actually lives. Commands
received on the ZMQ (socket) connection are relayed to the lantz driver.

The file for the instrument server, *instrument_server.py*, is located in the
main NSpyre folder (e.g. here it is *C:\GitHub\nspyre-org\nspyre*). It boots a
server with all the default arguments, which are located in the *config.yaml*
file located in the same folder.

*config.yaml* default arguments give a name to the instrument server
**(Experiment__Computer_1)**, define the port (5556), and instantiate the relevant
LANTZ drivers. The list of instruments and their corresponding drivers are
located in the device_list within the config.yaml file and would have to be
updated by the user.

The default settings in config.yaml include two test devices
``my_sg, osc``. Running instrument_server.py from your cmd window (with your nspyre
environment activated and from within the folder containing the file) would load
the two fake instruments currently specified.

.. code-block:: console
   
   (nspyre) C:\GitHub\nspyre\nspyre> python instrument_server.py
   Loaded my_sig in 0.087791s
   Loaded Oscars in 0.008976s
   Server ready…

View Manager
------------

We can now connect to and control all the devices that were loaded using the
instrument manager. We test that using the following code, which is given in
details in Notebook_Example.py within NSpyre, or in Jupyter Scripts/Alex's
tutorial/The Instrument Server and Spyrelet.ipynb:

.. code-block:: python
   
   # This command will be explained later
   %gui qt5
   
   # import libraries
   from nspyre import * # this import will be explained later
   from nspyre.instrument_manager import Instrument_Manager # for connect to device servers
   from nspyre.widgets.launcher import Spyrelet_Launcher_Widget, Combined_Launcher
   
   # this import will be explained later
   # for some weird reason Jupyter sometimes needs several runs of this command
   %gui qt5
   %gui qt5
   # Add all the instruments
   m = Instrument_Manager(timeout=10000)
   locals().update(m.get_devices())
   
>>> print('Available devices: ', list(m.get_devices().keys()))
Available devices:  ['my_sg', 'osc']
>>> # when done successfully the code would print this
>>> # control and manipulate the available devices with device-specific commands
>>> my_sg.frequency # read the currently set frequency, which we previously set to 10 kHz
10000.0 hertz
>>> my_sg.frequency = Q_(10,'Hz') # set the frequency to 10 Hz
>>> my_sg.frequency
10.0 hertz

Note that the instrument server we loaded, and the device parameters we control are
streamed to and saved in the mongo database.
