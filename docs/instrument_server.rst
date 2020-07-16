.. attention::
   
   We know some of these webpages could use some work -- this documentation has only recently been created and is in active development. It is updated regularly, so check back weekly.

The Instrument Server
=====================

The Instrument Server is where the lantz driver actually lives. Commands
received on the ZMQ (socket) connection are relayed to the lantz driver.

The file for the instrument server, *instrument_server.py*, is located in the
main NSpyre folder (e.g. here it is *C:\GitHub\NSpyre-Dev\nspyre*). It boots a
server with all the default arguments, which are located in the *config.yaml*
file located in the same folder.

*config.yaml* default arguments give a name to the instrument server
**(Experiment__Computer_1)**, define the port (5556), and instantiate the relevant
LANTZ drivers. The list of instruments and their corresponding drivers are
located in the device_list within the config.yaml file and would have to be
updated by the user.




Installation
------------


nspyre
^^^^^^
