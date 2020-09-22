# nspyre
[![GitHub license](https://img.shields.io/github/license/nspyre-org/nspyre)](https://github.com/nspyre-org/nspyre/blob/master/LICENSE)
[![Documentation Status](https://readthedocs.org/projects/nspyre/badge/?version=latest)](https://nspyre.readthedocs.io/en/latest/?badge=latest)

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

Now you need to initialize the replica set. To do so enter the mongo shell and input a rs.initiate command
```
mongo
rs.initiate({_id: "NSpyreSet", members:[{_id: 0, host: '0.0.0.0:27017'},{_id: 1, host: '0.0.0.0:27018'}]})
quit()
```
Finally, if you are planning on using NSpyre from different computers, you will also need to open the appropriate port in the firewall of the server machine (by default these are 27017 and 27018)

Finally you can create and configure a conda environment.  The pip command must be run from inside the nspyre folder (where the setup.py script is located). Additionally, some part of this install may require the shell to be started with admin rights:
```
conda create -n nspyre python=3
activate nspyre
pip install -e .
```

PyZMQ must be installed manually from within the conda environment with:
```
conda install pyzmq
```

Modify your nspyre/nspyre/config.yaml to suit your specific configuration of nspyre.
