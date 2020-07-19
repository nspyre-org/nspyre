.. attention::
   
   We know some of these webpages could use some work -- this documentation has only recently been created and is in active development. It is updated regularly, so check back weekly.

***************
Getting Started
***************

Lantz
-----

Full documentation for LANTZ is available at https://lantz.readthedocs.io/en/0.3/.
The basic layer on which NSpyere is based is called LANTZ. This framework is used to control and connect to instruments with different connectivities (server, ethernet, usb, etc.). Lantz contains drivers that create 3 types of attributes for each driver:

* Feature (Feat), which is a readonly or a read/write variable (e.g, the frequency of a signal generator, which you can both read and set).
* Dictionary feature (dicFeat), which works the same as @Feat, but is a dictionary of such Feats.
    
    - This is useful for instrument with several of the control or ability (i.e. a counting card with multiple channels)

* Action, which is a function that acts on the device (calibration, initialization, get an array of points, etc.)
    
    - In general, when it is a single variable that is easy to read or read/write that should be a @Feat. When it is more complicated it is usually an @Action.

In each driver file there will be imported libraries. The minimum you need is to import the driver and the attributes (Action, Feat, DicFeat, ureg), but other standardized libraries like numpy can also be imported. An example of a driver can be found in your lantz folder, in the ``drivers/`` subdirectory. Opening stanford/sg396 in your editor would show the driver for the signal generator.

The lantz docs linked above provide a very good introduction of a toy signal generator to so a typical use case.


