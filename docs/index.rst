.. nspyre documentation master file, created by
   sphinx-quickstart on Sat Jul 11 14:45:19 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to nspyre's documentation!
==================================

.. image:: https://img.shields.io/github/license/nspyre-org/nspyre
   :target: https://github.com/nspyre-org/nspyre/blob/master/LICENSE
   :alt: GitHub

.. image:: https://readthedocs.org/projects/nspyre/badge/?version=latest
   :target: https://nspyre.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

Pythonic Networked Scientific Experimentation Toolkit

.. toctree::
   :maxdepth: 4
   :caption: Contents
   :hidden:

   install
   getting_started
   spyrelet
   instrument_server
   the_database
   view_manager

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

NSpyre is a Python Framework for conducting physics experiments. It uses a
networked approach to allow for the running of experiments using distributed
equipment over many networked systems. The experimental hardware being controlled
can thus be connected to different computers, which can in turn be controlled by
another machine running the *experimental* commands. This allows for the easy
integration of shared resources in a research environment.

.. code-block:: console
   
   (conda env) $ python main.py

It's built on top of the Lantz (instrumentation communication toolkit) module
for interfacing with equipment using a variety of protocols and grew out of
many years of development in the Awschalom Group and others — first from many
years of LabView and Matlab code into an original *proto-spyre* in python,
and finally into it’s fully realized networked form.

How is it used?
===============

The beauty of NSpyre is that many operations can be performed in multiple ways,
allowing for maximum flexibility. This includes both command line, GUI, and
Jupyter interfaces. Experiments and analyses can be written in detailed
*spyrelets* or added in-situ in a scripting style fashion. This
*plug-and-play* fashion allows for many modalities, but here is a common usage:

.. nbinput:: ipython3
   :execution-count: 1
   
   %gui qt5
   from nspyre import *
   from nspyre.instrument_manager import Instrument_Manager
   from nspyre.widgets.launcher import Spyrelet_Launcher_Widget, Combined_Launcher

.. nbinput:: ipython3
   :execution-count: 2
   
   %gui qt5 #Sometimes jupyters needs a few runs of this commands for some weird reason

.. nbinput:: ipython3
   :execution-count: 3
   
   %gui qt5
   # Add all the instruments
   m = Instrument_Manager(timeout=10000)
   locals().update(m.get_devices())
   print('Available devices: ', list(m.get_devices().keys()))
   
   # Add all the spyrelets
   all_spyrelets = load_all_spyrelets()
   locals().update(all_spyrelets)
   print('Available spyrelets: ', list(all_spyrelets.keys()))
   
   # Clean up the mongo database if desired
   # drop_all_spyrelets(except_list=list(all_spyrelets.keys()))
   
   # Make a launcher
   launcher = Combined_Launcher(spyrelets=all_spyrelets)

Who uses it? (And who are we)
=============================

Primarily developed out of the Awschalom Group at the University of Chicago PME,
we are an experimental quantum physics research lab with a focus on *Spin Dynamics
and Quantum Information Processing in the Solid State*. There has been growing
adoption of nspyre in the immediate surroundings outside our doors, but there is
hope that this software can be adopted by more and more people from different
institutions and we can all benefit from these shared resources to lower the
development time for writing code and foster exchange to improve our research
and maximize our productivity. Anyone in the research or industrial spaces using
electrical or other computer controlled equipment with a programming interface
(or an already written Lantz driver) can benefit from these resources.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
