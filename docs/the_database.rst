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
your config.yaml file as mongodb://localhost:27017/, which means it is located
on this computer on port 27017.
