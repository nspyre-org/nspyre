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
   print('Available spyrelets: ', list(all_spyrelets.keys()))


Available spyrelets:  ['s2', 'my_exp']
# when successful the code would print this


Note that just like with the devices, the available spyrelets should be
specified in the config.yaml under experiment_list.
