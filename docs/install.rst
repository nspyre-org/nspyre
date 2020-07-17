.. important::
   
   These installation instructions are only temporary. A new
   streamlined installer is in development and will be released shortly. Updated
   documentation will follow.


*******
Install
*******

The following should be run in a standard windows cmd line or equivalent
(eg: https://cmder.net/) This is because you need to have git installed (ideally
hub, too) and on the path to perform the above installation from github. Bash
will also need to be enabled - will include directions for this soon. 


Install MongoDB
===============

- Download MongoDB v4.2.1 (or greater) from
  https://www.mongodb.com/download-center/community
- Install MongoDB v4.2.1 using default options
- Put the bin to the path variable (in system environment variable).
  For a standard install this will likely be something like
  ``C:\Program Files\MongoDB\Server\4.2\bin``.
  This will allow you to call MongoDB from the command line and is necessary for
  the install.bat script to work.

Install NSpyre
==============
Clone the repository

.. code-block:: console
   
   > git clone https://github.com/AlexBourassa/nspyre nspyre

Configure and start the MongoDB server; this will start two mongo servers in the
same replica set (one primary and one secondary). By default these are publicly
accessible on ports 27017 and port 27018 so if you are not in a secured private
network, make sure to add some security configurations to the `mongodb1.cfg` and
`mongodb2.cfg` files (better support for these security configurations will be
integrated in future versions).

.. code-block:: console
   
   > cd nspyre
   > install.bat

Now you need to initialize the replica set. To do so enter the mongo shell and
input a ``rs.initiate`` command

.. code-block:: console
   
   > mongo
   $ rs.initiate({_id:'NSpyreSet', members:[{_id:0, host:'0.0.0.0:27017'}, {_id:1, host:'0.0.0.0:27018'}]})
   $ quit()

Finally, if you are planning on using **NSpyre** from different computers, you
will also need to open the appropriate port in the firewall of the server
machine (by default these are 27017 and 27018).

Additionally, you can create and configure a conda environment. The pip command must
be run from inside the nspyre folder (where the setup.py script is located).
Additionally, some part of this install may require the shell to be started with
admin rights:

.. code-block:: console
   
   > conda create -n nspyre python=3
   > activate nspyre
   > pip install -e .

PyZMQ must be installed manually from within the conda environment with:

.. code-block:: console
   
   > conda install pyzmq

Modify your *nspyre/nspyre/config.yaml* to suit your specific configuration of
nspyre.
