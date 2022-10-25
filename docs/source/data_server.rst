###############
The Data Server
###############

The data server hosts experimental data. It has a collection of data sets, each 
of which contains a "source" and one or more "sinks". The "source" provides 
data to a data set and the "sinks" collect data from the data set.

To start the data server, simply run:

.. code-block:: bash

   nspyre-dataserv

Data can be pushed to the data server like so:

.. code-block:: python

    # source.py

    from nspyre import DataSource

    with DataSource('MyDataSet') as data_source:
        data_source.push({'some_data1': [1, 2, 3], 'some_data2': [4, 5, 6]})

The pushed data can be any `pickleable <https://docs.python.org/3/library/pickle.html>`__ 
Python object. While it is not strictly required, the argument to ``push()`` 
should be a Python dictonary so that data can be accessed from the data sink 
like so:

.. code-block:: python

    # sink.py

    from nspyre import DataSink

    with DataSink('MyDataSet') as data_sink:
        if data_sink.pop():
            print(data_sink.some_data1)
            print(data_sink.some_data2)

The data server is designed for use with streaming data. Each time ``push()`` 
is called, it creates a packet that is sent to the data server. It does not 
guarantee the delivery of any given packet sent to the server with ``push()`` 
and retrieved with ``pop()``. This is by design and can make your software 
more robust if used correctly: as long as newer packets strictly contain more 
data than older packets, your application should run smoothly.

This is an example of `BAD` data server useage:

.. code-block:: python

    from nspyre import DataSource

    with DataSource('MyDataSet') as data_source:
        for i in range(100):
            data = get_data()
            data_source.push({'mydata': data})

The problem is that each ``push()`` statement sends different data to the data 
server. If any packets are dropped, a connected sink could lose some 
potentially important data! A better implementation is:

.. code-block:: python

    from nspyre import DataSource

    data = []
    with DataSource('MyDataSet') as data_source:
        for i in range(100):
            data.append(get_data())
            data_source.push({'mydata': data})

In this example, every packet sent to the data server with ``push()`` contains 
some new data, but also the data taken in previous ``push()`` calls. This 
guarantees that any dropped packets will be of no consequence to any connected 
sinks.

This may seem like an unintuitive design, but imagine the following situation: 
the data source program calling ``push()`` is sending data faster 
than the data sink program calling ``pop()`` can process the data. An 
alternative data server implementation might block ``push()`` calls in the 
source if previous data has not yet been processed by the sink. This could 
introduce timing variation and uncertainty in the source, which is very 
undesirable if a scientific experiment is the source. Instead, if a sink object 
is not calling ``pop()`` fast enough to keep up with the source, the data 
server will start throwing away older packets (for that specific sink).

The data server is effectively a series of 
`FIFO buffers <https://en.wikipedia.org/wiki/FIFO_(computing_and_electronics)>`__.
For each data set, there is one FIFO buffer for the source and one for each of 
the sinks. ``push()`` queues data to the source FIFO. The data server dequeues 
data from the source FIFO, then queues a copy of that data on each of the sink 
FIFOs. Then the data server dequeues data from the sink FIFOs and sends it to 
the corresponding sink.
