Welcome to nspyre's documentation!
==================================

.. GitHub
.. image:: https://img.shields.io/github/v/release/nspyre-org/nspyre?label=GitHub
   :target: https://github.com/nspyre-org/nspyre/

.. PyPi version
.. image:: https://img.shields.io/pypi/v/nspyre
   :target: https://pypi.org/project/nspyre/

.. conda-forge version
.. image:: https://img.shields.io/conda/v/conda-forge/nspyre
   :target: https://github.com/conda-forge/nspyre-feedstock

.. License
.. image:: https://img.shields.io/github/license/nspyre-org/nspyre
   :target: https://github.com/nspyre-org/nspyre/blob/master/LICENSE

.. Docs build
.. image:: https://readthedocs.org/projects/nspyre/badge/?version=latest
   :target: https://nspyre.readthedocs.io/en/latest/?badge=latest

.. conda-forge platform
.. image:: https://img.shields.io/conda/pn/conda-forge/nspyre
   :target: https://github.com/conda-forge/nspyre-feedstock

.. DOI
.. image:: https://zenodo.org/badge/220515183.svg
   :target: https://zenodo.org/badge/latestdoi/220515183


(N)etworked (S)cientific (Py)thon (R)esearch (E)nvironment

.. toctree::
   :maxdepth: 4
   :caption: Contents
   :hidden:

   install
   getting_started
   data_server
   instrument_server

.. toctree::
   :maxdepth: 1
   :caption: Misc Guides
   :hidden:

   guides/ni-daqmx

.. toctree::
   :maxdepth: 6
   :caption: API
   :hidden:

   autoapi/index

.. toctree::
   :maxdepth: 2
   :caption: Contributing
   :hidden:
   
   contributing

What is nspyre?
===============

nspyre is a Python package for conducting scientific experiments. It provides 
a set of tools to allow for control of instrumentation, data collection, 
real-time plotting, as well as GUI generation. Anyone in the research or 
industrial spaces using computer-controlled equipment and collecting data can 
potentially benefit from using nspyre to run their experiments.

The hardware being controlled can be connected either locally on the machine 
running the experimental logic, or on a remote machine, which can be accessed 
in a simple, pythonic fashion. This allows for the easy integration of shared 
instrumentation in a research environment. Data collection is also 
networked, and allows for real-time viewing locally, or from a remote machine. 
nspyre provides a set of tools for quickly generating a Qt-based GUI for 
control and data viewing.

If you use nspyre for an experiment, we would really appreciate it if you 
(`cite <https://doi.org/10.5281/zenodo.7315077>`__) it in your publication!

Who we are, and why we made nspyre
==================================

nspyre is primarily developed out of the 
`Awschalom Group <https://pme.uchicago.edu/group/awschalom-group>`__ at the 
University of Chicago PME. We are an experimental quantum physics research lab 
with a focus on spin dynamics and quantum information processing. There are 
many software packages that seek to solve the same problems as nspyre. However, 
most suffer from being either:

1. Designed for a very specific type of experiment at the expense of generality
2. A commerical product that attempts to force users into buying the company's proprietary equipment

nspyre is free and open-source 
(`github <https://github.com/nspyre-org/nspyre>`__). Its design 
intent aspires to the Unix philosophy. It attempts to give the user a 
set of helpful tools, without forcing them to run their experiment in any 
specific way. We hope that others will find this software useful, and will 
:ref:`contribute <contribute>` to its development.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
