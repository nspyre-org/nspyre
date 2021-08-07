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

NSpyre is a Python package for conducting scientific experiments using lab instrumentation. It provides a set of tools to allow for networked control of instrumentation and data collection.

The hardware being controlled can be connected either locally on the machine running the experimental logic, or on a remote machine, which can be accessed in a simple, pythonic fashion. This allows for the easy integration of shared instrumentation in a research environment.

Data collection is similarly networked, and allows for real-time viewing locally, or from a remote machine. NSpyre also provides a set of tools for quickly generating a Qt-based GUI with control and data viewing.

NSpyre grew out of many years of development in the `Awschalom Group <https://pme.uchicago.edu/group/awschalom-group>`__ and others — first from many years of LabView and Matlab code into an original *proto-spyre* in Python, and finally into its networked form.

How is it used?
===============

Start an instrument server for hosting devices:

.. code-block:: console

   $ nspyre-inserv

Add instrument drivers to the instrument server:

.. code-block:: python

   'TODO'

Run your experiment:

.. code-block:: python

   import numpy as np
   from nspyre import InstrumentGateway, Q_

   # connect to the instrument server
   with InstrumentGateway() as gw:
      # microwave drive amplitude
      gw.sig_gen.amplitude = 0.5
      # frequency range to sweep over
      frequencies = np.linspace(2.5e9, 3.5e9, 100)
      # photoluminescence reading
      pl = np.zeros(len(frequencies))
      for i, f in enumerate(frequencies):
         gw.sig_gen.frequency = f
         pl[i] = gw.photodiode.read()

Who uses it? (And who are we)
=============================

Primarily developed out of the Awschalom Group at the University of Chicago PME, we are an experimental quantum physics research lab with a focus on *Spin Dynamics and Quantum Information Processing in the Solid State*. There has been growing adoption of nspyre in the immediate surroundings outside our doors, but there is hope that this software can be adopted by more and more people from different institutions and we can all benefit from these shared resources to lower the development time for writing code and foster exchange to improve our research and maximize our productivity. Anyone in the research or industrial spaces using computer controlled equipment can benefit from these resources.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
