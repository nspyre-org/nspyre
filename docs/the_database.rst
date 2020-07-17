.. attention::
   
   We know some of these webpages could use some work -- this documentation has only recently been created and is in active development. It is updated regularly, so check back weekly.

The Database & MongoDB
======================

The database, mongoDB, is where all the data acquired for each spyrelet is
streamed and stored. We can open the mongoDB app (called MongoDB Compass) and
see how our recent operation influenced the parameters stored within the
database.

For example, while testing the simulated instrument server, the last value we
set for the frequency of our sg  instrument was 10.0 Hz. We first open MongoDB
Compass and connect to our database. The database address should be specified in
your config.yaml file as ``mongodb://localhost:27017/``, which means it is located
on this computer on port 27017.

.. image:: images/mongoDB-connect.png

Under Experiment_Computer_1, our computer server name, we can see the list of devices, namely our 2 fake devices, my_sg and osc. Clicking on my_sg and scrolling to the frequency attribute reveals that it is a Feat, not a readonly attribute, has units of Hz, and its current value is indeed 10.

.. image:: images/mongoDB-my-sg.png

The data acquired while running s2 can be viewed by clicking on s2 found under Spyre_Live_Data. We can see the experiment created and indexed 20 objects, and for each it stored a random array and a frequency value (10 Hz). Notice that we can see that these are the parameters specified to be acquired in the *config.yaml* file.
