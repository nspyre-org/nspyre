.. nspyre documentation master file, created by
   sphinx-quickstart on Sat Jul 11 14:45:19 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to nspyre's documentation!
==================================

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

# a 79-char ruler:
# 34567891123456789212345678931234567894123456789512345678961234567897123456789
What is NSpyre?
=============

NSpyre is a Python Framework for conducting Physics 
It uses a networked approach to allow for the running of experiments using
distributed equipment over many networked systems. The experimental hardware
being controlled can thus be connected to different computers, which are in
turn be controlled by another machine running the *experimental setup*. This
allows for the easy integration of shared resources in a research environment.

[insert example usage codeblock]

It builds on top of the Lantz (instrumentation communication toolkit) module
for interfacing with equipment using a variety of protocols and grew out of
many years of development in the Awschalom Group and others — first from the
dark ages of LabView and Matlab code into an original proto-spyre and finally
into it’s fully realized networked form.

 Networked Scientific Experimentation Toolkit

How is it used?
============

The beauty of NSpyre is that many operations can be performed in multiple ways,
allowing for maximum flexibility. This includes both command line, GUI, and
Jupyter interfaces. Experiments and analyses can be written in detailed
*Spyrelets* or added in-situ/adhoc in a scripting style fashion. This
*plug-and-play* fashion allows for many modalities, but here is a common usage:

[insert example codeblock]

Who uses it? (And who are we)
========================

Primarily developed out of the Awschalom Group at the University of Chicago PME,
we are an experimental quantum physics research lab with a focus on point defect
in the solid-state. There has been growing adoption in the immediate quantum
space with our collaborations within our own halls, but there is hope that this
software can be adopted by more and more people from different institutions and
we can all benefit from these shared resources to low the development time
writing code and foster exchange to improve our research and maximize our
productivity. Anyone in the research or industrial spaces using electrical or
other computer controlled equipment with a programming interface can benefit
from these resources.


Installation
============

.. automodule:: Instrument_Server
   :members:

######
nspyre
######

Networked Scientific Python Research Environment

############
Installation
############

The following should be run in a standard windows cmd line or equivalent (eg: https://cmder.net/)

###############
Install MongoDB
###############

- Download mongodb v4.2.1 (or greater) from https://www.mongodb.com/download-center/community
- Install mongodb v4.2.1 using default options
- Put the bin to the path variable (in system environment variable).
  For a standard install this will likelly be something like C:\Program Files\MongoDB\Server\4.2\bin
  This will allow you to call mongod from the command line. and is necessary for the install.bat script to work

##############
Install NSpyre
##############

Clone the repository
```
git clone git@github.com:AlexBourassa/nspyre.git nspyre
```
or
```
git clone https://github.com/AlexBourassa/nspyre nspyre
```

Configure and start the MongoDB server (this will start two mongo server in the same replica set (one primary and one secondary)). By default these are publicly accessible on ports 27017 and port 27018 so if you are not in a secured private network, make sure to add some security configurations to the mongodb1.cfg and mongodb2.cfg files (better support for these security configurations will be integrated in future versions)
```
cd nspyre
install.bat
```

Now you need to initialize the replica set. To do so enter the mongo shell and input a rs.initiate command
```
mongo
rs.initiate({_id: "NSpyreSet", members:[{_id: 0, host: 'localhost:27017'},{_id: 1, host: 'localhost:27018'}]})
quit()
```
Finally, if you are planning on using NSpyre from different computers, you will also need to open the appropriate port in the firewall of the server machine (by default these are 27017 and 27018)

Finally you can create and configure a conda environment.  The pip command must be run from inside the nspyre folder (where the setup.py script is located). Additionally, some part of this install may require the shell to be started with admin rights:
```
conda create -n nspyre python=3
activate nspyre
pip install -e .
```

Modify your nspyre/nspyre/config.yaml to suit your specific configuration of nspyre.



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
