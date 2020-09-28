.. attention::
   
   We know some of these webpages could use some work -- this documentation has only recently been created and is in active development. It is updated regularly, so check back weekly.

The Database & MongoDB
======================

A database, mongoDB, is used by nspyre to store experimental data collected by spyrelets, as well as centralize shared data used by different parts of the system. To start the database, run ``nspyre-mongodb``. This will do several things: first, it shuts down any currently running instances of mongodb. Next, it moves the database files from any previous run into a backups folder located at 
``/path/to/nspyre/mongodb/db_files_backup``
If you are using conda, this will be in
``/path/to/conda/envs/<conda env name>/lib/python3.8(or current python version)/site-packages/nspyre/mongodb/db_files_backup``.
Finally, it starts and initializes a new database instance.

If you want to directly view data in the database in real-time, you can download `MongoDB Compass`_ and connect via the same ``mongodb_addr`` specified in the client and server `configuration files`_, e.g. ``mongodb://localhost:27017/``

.. _MongoDB Compass: https://www.mongodb.com/try/download/compass

.. image:: images/mongoDB-connect.png
