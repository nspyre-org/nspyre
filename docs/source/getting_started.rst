###############
Getting Started
###############

The quickest way to get started is to clone the nspyre 
`template <https://github.com/nspyre-org/template>`__. This template contains a mock
experiment codebase that utilizes nspyre and demonstrates many of its features.
There are also `code examples <https://github.com/nspyre-org/examples>`__ provided by
other users. A brief description of some of nspyre's features are given here. An 
experiment utilizing the full capabilities of nspyre can be broken down into 
a few pieces of functionality:

The Instrument Server
=====================

The InstrumentServer is a tool that allows the user to create a networked 
server which hosts a collection of instrument drivers. It is basically a 
wrapper around `rpyc <https://rpyc.readthedocs.io/en/latest/>`__. The code 
below demonstrates the creation of an InstrumentServer.

.. code-block:: python

   # inserv.py

   from pathlib import Path

   from nspyre import serve_instrument_server_cli
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
      serve_instrument_server_cli(inserv)

Running this Python code will start the instrument server:

.. code-block:: bash

   python inserv.py

The Data Server
===============

The :ref:`data server <data_server>` hosts experimental data. It has a collection of data sets, each 
of which contains a "source" and one or more "sinks". The "source" provides 
data to a data set and the "sinks" collect data from the data set.

To start the data server, simply run:

.. code-block:: bash

   nspyre-dataserv

The Experiment
==============

Once the instrument and data servers have been started, we can run our 
experiment. The InstrumentGateway provides a connection to the InstrumentServer 
and its devices. We can create a data set on the data server and provide data 
to it by creating a DataSource. A simple experiment might look something like 
this:

.. code-block:: python

   import time

   import numpy as np
   from nspyre import DataSource
   from nspyre import InstrumentGateway

   # connect to the instrument server and data server
   with InstrumentGateway() as gw, DataSource('MyDataSet') as data:
      # frequencies that will be swept over in the measurement
      frequencies = np.linspace(start, stop, num_points)
      # photon counts corresponding to each frequency
      counts = np.zeros(num_points)
      # access the signal generator driver on the instrument server and its amplitude for the scan
      gw.sg.set_amplitude(6.5)
      # sweep counts vs. frequency
      for i, f in enumerate(frequencies):
         # set the signal generator frequency
         gw.sg.set_frequency(f)
         # wait for counts to accumulate
         time.sleep(0.1)
         # read the number of photon counts received by the DAQ
         counts[i] = gw.daq.cnts(1)
         # save the current data to the data server
         data.push({'freqs': frequencies, 'counts': counts, 'idx': i})


GUI and Plotting
================

The starting point for an nspyre GUI is ``nspyreApp``, which creates a template
Qt application with the default look and feel of nspyre. ``MainWidget`` 
provides a list of other widgets that the user can load into the GUI, as well 
as a convenient dockable interface for rearranging widgets. The code below 
creates a GUI that can load one of the nspyre plotting widgets, 
``FlexLinePlotWidget``, and a theoretical user-defined experiment widget 
``ExampleExperiment``.

.. code-block:: python

   import nspyre.gui.widgets.flex_line_plot_widget
   from nspyre import MainWidget
   from nspyre import MainWidgetItem
   from nspyre import nspyreApp
   
   import mygui
   
   # create a Qt application and apply nspyre visual settings
   app = nspyreApp()

   # create the GUI which allows launching of user widgets
   main_widget = MainWidget({
      'Experiments': {
         'ExampleExperiment': MainWidgetItem(mygui, 'ExampleExperiment')
      }
      'Plots': {
         'FlexLinePlot': MainWidgetItem(nspyre.gui.widgets.flex_line_plot_widget, 'FlexLinePlotWidget')
      },
   })
   main_widget.show()
   # Run the GUI event loop.
   app.exec()
