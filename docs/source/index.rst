Welcome to NSpyre's documentation!
==================================

.. image:: https://img.shields.io/github/license/nspyre-org/nspyre
   :target: https://github.com/nspyre-org/nspyre/blob/master/LICENSE
   :alt: GitHub

.. image:: https://readthedocs.org/projects/nspyre/badge/?version=latest
   :target: https://nspyre.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

Networked Scientific Python Research Environment

.. toctree::
   :maxdepth: 4
   :caption: Contents
   :hidden:

   install
   getting_started
   spyrelet
   instrument_server
   view_manager

.. toctree::
   :maxdepth: 1
   :caption: Misc Guides
   :hidden:

   guides/ni-daqmx

.. toctree::
   :maxdepth: 1
   :caption: API
   :hidden:
   
   api

.. toctree::
   :maxdepth: 2
   :caption: Contributing
   :hidden:
   
   contributing

What is NSpyre?
===============

NSpyre is a Python package for conducting scientific experiments using lab 
instrumentation. It provides a set of tools to allow for networked control of 
instrumentation, data collection, real-time data plotting, and GUI generation.

The hardware being controlled can be connected either locally on the machine 
running the experimental logic, or on a remote machine, which can be accessed 
in a simple, pythonic fashion. This allows for the easy integration of shared 
instrumentation in a research environment.

Data collection is similarly networked, and allows for real-time viewing 
locally, or from a remote machine. NSpyre also provides a set of tools for 
quickly generating a Qt-based GUI with control and data viewing.

NSpyre grew out of many years of development in the `Awschalom Group <https://pme.uchicago.edu/group/awschalom-group>`__ and others — first from many years of LabView and Matlab code into an original *proto-spyre* in Python, and finally into its networked form.

How is it used?
===============

Create a folder for log files:

.. code-block:: bash

   mkdir logs

Generate an instrument server for hosting device drivers:

.. code-block:: python

   # inserv.py

   import logging
   from pathlib import Path

   from nspyre import inserv_cli
   from nspyre import InstrumentServer
   from nspyre import nspyre_init_logger

   HERE = Path(__file__).parent

   # log to the console as well as a file inside the logs folder
   nspyre_init_logger(
      logging.INFO,
      log_path=HERE / 'logs',
      log_path_level=logging.DEBUG,
      prefix='inserv',
      file_size=10_000_000,
   )

   # create a new instrument server
   with InstrumentServer() as inserv:
      # create signal generator driver
      # 'sg' will be an instance of the class 'SigGen' in the file ./drivers/sg.py
      inserv.add('sg', HERE / 'drivers' / 'sg.py', 'SigGen')
      # create data acquisition instrument driver
      # 'daq' will be an instance of the class 'DAQ' in the file ./drivers/daq.py
      inserv.add('daq', HERE / 'drivers' / 'daq.py', 'DAQ')

      # run a CLI (command-line interface) that allows the user to enter
      # commands to control the server
      inserv_cli(inserv)

Start the instrument server:

.. code-block:: bash

   python inserv.py

Start the data server that stores experimental data:

.. code-block:: bash

   nspyre-dataserv

Run your experiment:

.. code-block:: python

   import logging
   from pathlib import Path
   import time

   import numpy as np
   from nspyre import DataSource
   from nspyre import InstrumentGateway

   HERE = Path(__file__).parent

   # log to the console as well as a file inside the logs folder
   nspyre_init_logger(
      log_level=logging.INFO,
      log_path=HERE / 'logs',
      log_path_level=logging.DEBUG,
      prefix='odmr',
      file_size=10_000_000,
   )

   # connect to the instrument server
   # connect to the data server and create a data set, or connect to an
   # existing one with the same name if it was created earlier.
   with InstrumentGateway() as gw, DataSource('ODMR') as odmr_data:
      # frequencies that will be swept over in the ODMR measurement
      frequencies = np.linspace(start, stop, num_points)

      # photon counts corresponding to each frequency
      counts = np.zeros(num_points)

      # set the signal generator amplitude for the scan (dBm).
      gw.sg.set_amplitude(6.5)

      # sweep counts vs. frequency.
      for i, f in enumerate(frequencies):
         # access the signal generator driver on the instrument server and set its frequency.
         gw.sg.set_frequency(f)
         # wait for counts to accumulate.
         time.sleep(0.1)
         # read the number of photon counts received by the DAQ.
         counts[i] = gw.daq.cnts(1)
         # save the current data to the data server.
         odmr_data.push({'freqs': frequencies, 'counts': counts, 'idx': i})

Who uses it? (And who are we)
=============================

Primarily developed out of the Awschalom Group at the University of Chicago PME, we are an experimental quantum physics research lab with a focus on *Spin Dynamics and Quantum Information Processing*. There has been growing adoption of nspyre in the immediate surroundings outside our doors, but there is hope that this software can be adopted by more and more people from different institutions and we can all benefit from these shared resources to lower the development time for writing code and foster exchange to improve our research and maximize our productivity. Anyone in the research or industrial spaces using computer controlled equipment can benefit from these resources.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
