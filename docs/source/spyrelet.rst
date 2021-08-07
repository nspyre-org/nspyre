.. attention::
   
   We know some of these webpages could use some work -- this documentation has only recently been created and is in active development. It is updated regularly, so check back weekly.

Spyrelets
=========

Spyrelet can run on any computer (even one that isn't connected to the actual
instrument) and implement the experimental logic. You can have different
instances of Spyrelet, but you should name them differently so they won't
override each other's data on the database.

Every spyrelet would contain the name of the relevant devices, a main function
for the actual experimental logic, and usually also include the initialize() and
finalize() functions. Note that the parameters for your main function must match
the ones in the initialize() and finalize() functions. The code for our
test spyrelet can be loaded from nspyre\nspyre\user\test_spyrelets.py or
C:\Jupyter Scripts\Alex's tutorial\Spyrelet_test.ipynb.

Now we can load our test spyrelet by going back to our original instrument
server code we implemented above (file Notebook_Example.py within NSpyre, or in
Jupyter Scripts/Alex's tutorial/The Instrument Server and Spyrelet.ipynb) and
uncomment/add the following:

.. code-block:: python

   # Add all the spyrelets
   all_spyrelets = load_all_spyrelets()
   locals().update(all_spyrelets)

>>> print('Available spyrelets: ', list(all_spyrelets.keys()))
>>> # when successful the code would print this
Available spyrelets:  ['s2', 'my_exp']

Note that just like with the devices, the available spyrelets should be
specified in the config.yaml under experiment_list:

.. code-block:: python
   
   # Experiment list
   # Each experiment entry should have an
   # alias:
   #   class: 'spyrelet class'
   #   spyrelets: A dictionary containing the sub-spyrelet to be used
   #   args: Argument used to instanciate the spyrelet.  This included device alias dict, spyrelets dict and other CONSTS parametters
   experiment_list:
     s2:
       class: nspyre.user.test_spyrelets.SubSpyrelet
       args:
         device_alias: {sg: my_sg}
     
     my_exp:
       class: nspyre.user.test_spyrelets.MyExperiment
       spyrelets: {s2: s2}
       args: {device_alias: {sg: my_sg, osc: osc}}

It is easy to see here how quickly one can rerun this process if an error occurred, without any need to reload the entire interface. Let’s try to run the s2 experiment defined as the SubSpyrelet class within the test spyrelet. We do that using the run, or background run commands:

>>> # run s2 experiment and halt the framework until it stops running
>>> s2.run(100,1.1)
100% ################ 100/100 [00:11<00:00, 8.85it/s]
>>> # run s2 in the background so the rest of the framework can keep working
>>> s2.bg_run(100,1.1)
<Thread(Thread-7, started 29612)>
100% ################ 100/100 [00:11<00:00, 8.62it/s]

As the experiment runs, the parameters being acquired by the test spyrelet are streamed to the database, as can be seen in the next section.
