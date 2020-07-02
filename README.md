# nspyre
Networked Scientific Python Research Environment

## Installation

The following should be run in a standard windows cmd line or equivalent (eg: https://cmder.net/)

#### Install MongoDB
- Download mongodb v4.2.1 (or greater) from https://www.mongodb.com/download-center/community
- Install mongodb v4.2.1 using default options
- Put the bin to the path variable (in system environment variable).  
  For a standard install this will likelly be something like C:\Program Files\MongoDB\Server\4.2\bin
  This will allow you to call mongod from the command line. and is necessary for the install.bat script to work

#### Install NSpyre
Clone the repository
```
git clone git@github.com:AlexBourassa/nspyre.git nspyre
```
or 
```
git clone https://github.com/AlexBourassa/nspyre nspyre
```

Configure and start the MongoDB server (this will start two mongo server in the same replica set (one primary and one secondary)). By default these are publicly accessible on ports 27017 and port 27018 so if you are not in a secured private network, make sure to add some security configurations to the mongodb1.cfg and mongodb2.cfg files (better support for these security configurations will be integrated in future versions)
```
cd nspyre
install.bat
```

Now you need to initialize the replica set. To do so enter the mongo shell and input a rs.initiate command (where you should substitute the X.X.X.X with your computer's ip address
```
mongo
rs.initiate({_id: "NSpyreSet", members:[{_id: 0, host: 'X.X.X.X:27017'},{_id: 1, host: 'X.X.X.X:27018'}]})
quit()
```
Finally, if you are planning on using NSpyre from different computers, you will also need to open the appropriate port in the firewall of the server machine (by default these are 27017 and 27018)

Finally you can create and configure a conda environment.  The pip command must be run from inside the nspyre folder (where the setup.py script is located). Additionally, some part of this install may require the shell to be started with admin rights:
```
conda create -n nspyre python=3
activate nspyre
conda install pyzmq
pip install -e .
pip install git+https://github.com/pyqtgraph/pyqtgraph.git
```
To ensure that you can view your data correctly, make sure that line 45 of nspyre/widgets/main.py activates the name of your aniconda environment (if you copied the code above, this would mean you should have 
```
cmd = 'bash -c "activate nspyre; python {}"'.format(filename) 
```
You will also need to make sure to install lantz (most likelly a local distribution). Here an example of what that lantz installation could look like (feel free to modify this as needed).
```
cd ..
git clone https://github.com/awsch/lantz lantz
cd lantz
pip install -e .
```
