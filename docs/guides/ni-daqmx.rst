************************
NI-DAQmx Python Tutorial
************************

This script is meant to serve as a quickstart tutorial and future
reference for working with the nidaqmx Python package to interface with
the NI-DAQmx data acquisition toolset. Throughout this tutorial,
''nidaqmx'' will refer to the Python package and ''NI-DAQmx'' will refer
to the NI data acquisition driver and runtime environment -- consistent
with the National Instruments nomenclature. Running nidaqmx requires
NI-DAQmx or NI-DAQmx Runtime. Visit https://ni.com/downloads to download
the latest version of NI-DAQmx.

nidaqmx can be installed with pip:

.. code-block:: console

   python -m pip install -U nidaqmx

The nidaqmx package contains an API (Application Programming Interface)
for interacting with the NI-DAQmx driver. The package was created and
is supported by National Instruments. The package is implemented as a
complex, highly object-oriented wrapper around the NI-DAQmx C API using
the ctypes Python library.

The C API is included in any version of the driver that supports it. The
nidaqmx package does not require installation of the C header files.
Some functions in the nidaqmx package may be unavailable with earlier
versions of the NI-DAQmx driver.

nidaqmx supports only the Windows operating system.


Some helpful resources when working with nidaqmx
------------------------------------------------

Reference Materials and Manuals:
    * NI-DAQmx C Reference Help:
        [1] https://zone.ni.com/reference/en-XX/help/370471AM-01/
    * NI-DAQmx Terminal Names:
        [2] https://www.ni.com/documentation/en/ni-daqmx/latest/mxcncpts/termnames/
    * DAQ X Series User Manual:
        [3] https://www.ni.com/pdf/manuals/370784k.pdf
    * NI PCIe-6343 Supported Properties: (most common DAQ in QML/PME labs)
        [4] https://zone.ni.com/reference/en-XX/help/370471AM-01/cdaqmxsupp/pcie-6343/

Getting Started, How Tos, and Guides:
    * 10 Most Important NI-DAQmx Functions:
        [5] https://www.ni.com/en-gb/support/documentation/supplemental/06/learn-10-functions-in-ni-daqmx-and-handle-80-percent-of-your-dat.html
    * Understanding NI-DAQmx Timing and Synchronization:
        [6] https://www.ni.com/en-gb/support/documentation/supplemental/06/timing-and-synchronization-features-of-ni-daqmx.html
    * Getting Started with NI-DAQmx (LabVIEW):
        [7] https://www.ni.com/tutorial/5469/en/


See https://nidaqmx-python.readthedocs.io/en/latest/ for more details.
See GitHub for the latest source.

.. code-block::  python

   import nidaqmx
   from nidaqmx.constants import (AcquisitionType, CountDirection, Edge,
       READ_ALL_AVAILABLE, TaskMode, TriggerType)
   from nidaqmx.stream_readers import CounterReader
   import numpy

The NI-DAQmx driver is fundamentally written in C along with an
interface using the .NET Framework. The DAQmx API is simply a set of
libraries containing functions on how to perform all data
acquisition operations. These APIs include support for
LabWindows/CVI, C, C++, Visual Basic 6.0, VB.NET and C#, but all
interface with the data aquisition hardware through the C core
libraries. The nidaqmx Python package is an extension of these
resources to provide official support for Python.

If you are already familiar with using NI-DAQmx in LabVIEW, or using
LabVIEW in general, then you are in luck. Data acquisition using any
officially supported text-based programming environment is very
similar to the LabVIEW NI-DAQmx programming interface, as the
function calls in these environments are the same as the NI-DAQmx
VI's. This is because all equivalent function calls between
languages refer to the same function call in the C core libraries.

The current documentation of the nidaqmx package is limited. Since
all the APIs interface with the common C core libraries, it is
therefore recommended that you refer to the NI-DAQmx C Reference [1]
as you begin using nidaqmx. An effective method at gaining
familiarity and making quick progress with nidaqmx is to search for
the C core function that implements the functionality you require.
Then, search the nidaqmx source code (e.g. on GitHub) for references
to this C function call to find the required nidaqmx object and
associated attribute(s) which implement the necessary functionality.

In addition to the function calls in supported environments being
the same as the NI-DAQmx VI's, nearly all official documentation
on using NI-DAQmx to perform data acquisition operations and
how to implement software functionality are written using
LabVIEW as the environment. Fortunately, the data structure and
programming framework are consistent between environments and there
is a translation between LabVIEW components and Python objects,
attributes, etc.

In general, data acquisition programming with DAQmx involves the
following steps:

    * Create a Task and Virtual Channels
    * Configure the Timing Parameters
    * Start the Task
    * Perform a Read operation from the DAQ
    * Perform a Write operation to the DAQ
    * Stop and Clear the Task.

For (nearly) every NI-DAQmx LabVIEW VI, there is an associated
Python object in nidaqmx. Each NI-DAQmx LabVIEW property node has an
associated object attribute in Python, with the object typically
corresponding to the VI immediately preceding the property node in
the LabVIEW block diagram; other times, the associated attribute in
Python is of the Task class when the property node specifies more
generic functionality. A brief reference of the most commonly used
VI's and property nodes is given below:


+-----------------------------------+---------------------------+-----------------------+
| [NI-DAQmx VI]                     |                           | [Python class]        |
+===================================+===========================+=======================+
| Task VI                           | -> task = nidaqmx.Task()  | (Task)                |
+-----------------------------------+---------------------------+-----------------------+
| Create Virtual Channel VI         | -> task.ai_channels       | (AIChannelCollection) |
|                                   |    task.ao_channels       | (AOChannelCollection) |
|                                   |    task.ci_channels       | (CIChannelCollection) |
|                                   |    task.co_channels       | (COChannelCollection) |
|                                   |    task.di_channels       | (DIChannelCollection) |
|                                   |    task.do_channels       | (DOChannelCollection) |
+-----------------------------------+---------------------------+-----------------------+
| Trigger VI                        | -> task.triggers          | (Triggers)            |
+-----------------------------------+---------------------------+-----------------------+
| Timing VI                         | -> task.timing            | (Timing)              |
+-----------------------------------+---------------------------+-----------------------+
| Start Task VI                     | -> task.start()           |                       |
+-----------------------------------+---------------------------+-----------------------+
| Read VI                           | -> task.read()            |                       |
|                                   |    task.in_stream         | (InStream)            |
|                                   |    (see stream_readers)   |                       |
+-----------------------------------+---------------------------+-----------------------+
| Write VI                          | -> task.write()           |                       |
|                                   |    task.out_stream        | (OutStream)           |
|                                   |    (see stream_writers)   |                       |
+-----------------------------------+---------------------------+-----------------------+
| Wait Until Done VI                | -> task.wait_until_done() |                       |
|                                   |    task.is_task_done()    |                       |
+-----------------------------------+---------------------------+-----------------------+
| Stop Task VI                      | -> task.stop()            |                       |
+-----------------------------------+---------------------------+-----------------------+
| Clear Task VI                     | -> task.close()           |                       |
+-----------------------------------+---------------------------+-----------------------+

+-----------------------------------+-----------------------------------------------------------+
| [NI-DAQmx Propety Node]           |                                                           |
+===================================+===========================================================+
| Channel                           | -> task.[channel type]_channels[channel index].[property] |
+-----------------------------------+-----------------------------------------------------------+
| Timing                            | -> task.timing.cfg_samp_clk_timing(*args, **kwargs)       |
+-----------------------------------+-----------------------------------------------------------+

Notice how each VI's Python equivalent is initialized or called from
the Task class. Virtual channels and tasks are fundamental
components of NI-DAQmx. As the nidaqmx Python package aims to be a
highly object-oriented wrapper (in comparison to the other
supported environments) around the C API, the essential object
around which nidaqmx functions is the Task class. All other class
objects (particularly Channel class objects) are initialized within
the object of the Task class to whom the channel, trigger, timing,
or IO stream modifies. (For more information on the core NI-DAQmx
functions needed to implement a data acquisition scheme, see the
primer '10 Most Important NI-DAQmx Functions' [5].)

Virtual channels, or sometimes referred to generically as channels,
are software entities that encapsulate the physical (hardware)
channel along with other channel specific information — range,
terminal configuration, and custom scaling — that formats the data.

Conceptually, a task represents a measurement or generation you want
to perform. Tasks are collections of one or more virtual channels
with timing, triggering, and other properties. All channels in a
task must be of the same I/O type, such as analog input or counter
output. However, a task can include channels of different
measurement types, such as an analog input temperature channel and
an analog input voltage channel. The Python Task class in nidaqmx
has a Collection container for each type of physical channel, to
which Channel objects of the corresponding class are added using the
appropriate add_[channel type]_[measurement type] method for the
desired measurement type.

With all this background knowledge out of the way, let's walk
through an example of using nidaqmx to load the NI-DAQmx system
connected to the local machine, create tasks to count digital
edges on a counter using the digital input Sample Clock.

.. code-block:: python

   # Let's load up the NI-DAQmx system that is visible in the
   # Measurement & Automation Explorer (MAX) software of NI-DAQmx for
   # the local machine.
   system = nidaqmx.system.System.local()
   # We know on our current system that our DAQ is named 'DAQ1'
   DAQ_device = system.devices['DAQ1']
   # create a list of all the counters available on 'DAQ1'
   counter_names = [ci.name for ci in DAQ_device.ci_physical_chans]
   print(counter_names)
   # note that using the counter output channels instead of the inputs
   # includes the '[device]/freqout' output, which is not a counter
   print([co.name for co in DAQ_device.co_physical_chans])

National Instruments DAQ devices do not have separate Sample Clocks
for their counter channels. Therefore, either the Sample Clock of the
internal analog (or digital) channels, or an external Sample Clock,
must be specified when the counter requires timing functionality. If
no other analog (or digital) measurement is needed, then a 'dummy'
task must be created to start the Sample Clock for the counter.

.. code-block:: python

   # Let's create a task for the counter channel and a task for a
   # 'dummy' digital input channel to start the digital input Sample
   # Clock. A ''with'' code block is used to implement automatic error
   # handling and correctly stop and clear resources for each task
   # when the program exits.
   with nidaqmx.Task() as read_task, nidaqmx.Task() as samp_clk_task:
       # create a digital input channel on 'port0' of 'DAQ1'
       samp_clk_task.di_channels.add_di_chan('DAQ1/port0')
           """
           Note that port 2 of a DAQ device does not support buffered
           operations, so here port port0 is used. Additionally, the
           line_grouping Arg (1 channel for all lines or 1 channel
           per line) does not matter because this is a 'dummy' task.
           """

       # configure the timing parameters of the sample clock so that
       # it has a sampling rate of 100 Hz and runs continuously so
       # that the digital input sample clock continues to run even if
       # it's associated task is not reading anything from the channel.
       sampling_rate = 100
       samp_clk_task.timing.cfg_samp_clk_timing(rate,
                                       sample_mode=AcquisitionType.CONTINUOUS)
       # commit the task from the Reserved state in system memory to
       # the Commit state on the DAQ; this programs the hardware
       # resources with those settings of the task which must be
       # configured before the task transitions into the Start state.
       # This speeds up the execution of the samp_clk_task.start() call
       # because the hardware will now be in the Commit state and must
       # only transition to the State state to run the task.
       samp_clk_task.control(TaskMode.TASK_COMMIT)


       # create a counter input channel using 'ctr0' on 'DAQ1' to count
       # rising digital edges, counting up from initial_count
       read_task.ci_channels.add_ci_count_edges_chan(
                                   'DAQ1/ctr0',
                                   edge=Edge.RISING,
                                   initial_count=0,
                                   count_direction=CountDirection.COUNT_UP)

       # set the input terminal of the counter input channel on which
       # the counter receives the signal on which it counts edges
       read_task.ci_channels.all.ci_count_edges_term = '/DAQ1/PFI5'
          """
          When specifying the name of a terminal, all external
          terminals - as defined by NI-DAQmx - must include a leading
          '/' in its string. An external terminal is any terminal that
          can be routed internally from one channel to another or from
          DAQ to another; examples include: PFI lines, Sample Clocks,
          physical analog channels, physical digital channels, the
          output of a physical counter, etc. All external terminals
          can be 'exported' using task.export_signals.export_signal(
          *args). NI-DAQmx recognized devices do not include a leading
          '/' in their string name because they are not terminals.
          """

       # set the timing parameters of the counter input channel, using
       # the digial input Sample Clock as it's source, with the same
       # sampling rate used to generate the Sample Clock; the task will
       # work if a different sampling rate is set than the true rate
       # of the Sample Clock, but the hardware will not be optimized
       # for this clock signal. Additionally, set the counter to
       # readout its count to the buffer on the rising edge of the
       # Sample Clock signal.
       """ max counter sampling rate allowed: 100e6 (i.e. 100MHz)"""
       read_task.timing.cfg_samp_clk_timing(sampling_rate, source='/DAQ1/di/SampleClock',
           active_edge=Edge.RISING, sample_mode=AcquisitionType.CONTINUOUS)
           """
           Other optional Arg is 'samps_per_chan': if ** sample_mode**
           is **CONTINUOUS_SAMPLES**, NI-DAQmx uses this value to
           determine the buffer size. 'cfg_samp_clk_timing' returns an
           error if the specified value is negative.
           """
       # set the buffer size of the counter, such that, given the
       # sampling rate at which the counter reads out its current value
       # to the buffer, it will give two minutes of samples before the
       # buffer overflows.
       read_task.in_stream.input_buf_size = 12000


When a device controlled by NI-DAQmx does something, it performs
an action. Two very common actions are producing a sample and
starting a waveform acquisition. (Although we are doing neither
here, the digital input channel configured in samp_clk_task is
setup for a waveform acquisition, except the samp_clk_task.read(
*args) operation is never given to read any waveforms.)

Every NI-DAQmx action needs a stimulus or cause. When the
stimulus occurs, the action is performed. Causes for actions are
called triggers.
    * A start trigger initiates an acquisition or generation.
    * A reference trigger establishes the location, in a set of
      acquired samples, where pretrigger data ends and
      posttrigger data begins.
Both of these triggers can be configured to occur on a digital
edge, an analog edge, or when an analog signal enters or leaves
a window. (Other triggers include: arm start trigger [for
counters only], pause trigger, and handshake trigger.)

To set the parameters of a trigger, use the attributes of the
corresponding trigger object associated to the task to which
the trigger should apply; the Task class has a Triggers
container which holds all of its associated triggers. The start
and reference triggers are used so frequently that they can be
set using a cfg_[detection type]_[trigger type] method - from
their respective StartTrigger and ReferenceTrigger classes -
instead of assigning the trigger attributes individually.

.. code-block:: python

   # Create an arm start trigger for the counter so that it is
   # synced with the digital input Sample Clock and only starts
   # counting when the first Sample Clock tick is detected. This
   # prevents the necessity of throwing out the first sample in the
   # counter buffer (due to the uncertainity in the collection
   # window of the first sample because it is set by when the
   # counter and Sample Clock start operating
   read_task.triggers.arm_start_trigger.trig_type = TriggerType.DIGITAL_EDGE
   read_task.triggers.arm_start_trigger.dig_edge_edge = Edge.RISING
   read_task.triggers.arm_start_trigger.dig_edge_src = '/DAQ1/di/SampleClock'

There are two primary ways in which I/O can be read (written)
from (to) a device by nidaqmx. The first is to call the read
(write) method of the associated task and have it return (write)
the data given the arguments passed. For small read and
infrequent write operations, this is an acceptable method.
However, for large and/or frequent read (write) operations, I/O
streams should be used instead.

To this end, nidaqmx has a set of stream reader (writer) classes
for the different types of channels. Each task's read (write)
stream is given by the Instream (OutStream) returned by
task.in_stream (task.out_stream). These stream readers (writers)
require a buffer to be passed from which it can directly read
(write) to; if the buffer is not the appropriate size an error
will be thrown.

.. code-block:: python

   # create a counter reader to read from the counter InStream
   reader = CounterReader(read_task.in_stream)
   # start the tasks to begin data acquisition; note that because
   # the arm start trigger of the counter was set, it does not
   # matter which task is started first, the tasks will be synced
   samp_clk_task.start()
   read_task.start()
   # create a data buffer for the counter stream reader
   data_array = numpy.zeros(12000, dtype=numpy.uint32)
   # read all samples from the counter buffer to the system memory
   # buffer data_array; if the buffer is not large enough, it will
   # raise an error
   reader.read_many_sample_uint32(data_array,
       number_of_samples_per_channel=READ_ALL_AVAILABLE)



After completing a task, stop the task. If it will no longer be
used, clear the task to de-allocate all reserved resources. The
nidaqmx task.close() method clears the specified task. If the
task is currently running, the function first stops the task and
then releases all of its resources. Once a task has been closed,
it cannot be used unless it is recreated by re-adding channels
any other parameters; it does not need to be reinitialized.
Thus, if a task will be used again, the nidaqmx task.stop()
function should be used to stop the task, but not clear it; then
task.start() will continue the task again.

.. code-block:: python

   # NOTE: the below calls do not need to be used at the end of a
   # code block when a 'with' block is implemented for task
   # creation; this is handled automatically. The below lines are
   # for illustration purposes.
   # pause the data acquisition
   read_task.stop()
   # continue the data aquisition
   read_task.start()
   # stop the data acquisition and free the system resources
   read_task.close()
   # the task 'read_task' can no longer be used;
   # read_task.start() will now raise an error.

The nidaqmx Python package handles errors raised my NI-DAQmx through
its DaqError and DaqWarning Exception classes and passes them along
in Python with any associated error messages. Thus, any error or
warning from nidaqmx can be caught uses DaqError and DaqWarning. It
is suggested that any program utilized nidaqmx handle these
exceptions appropriately.

This is the end of the tutorial (for now). Please see the references
and guides listed above, or the nidaqmx documentation at
https://nidaqmx-python.readthedocs.io/en/latest/ for more
information. The Class and method docstrings included with the
nidaqmx source code provide thorough information of how to set their
arguments and what data the return types provide.
