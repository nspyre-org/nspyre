# nspyre
Networked Scientific Python Research Environment

## Installation
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

Configure and start the MongoDB server
```
cd nspyre
install.bat
```

Create and configure a conda environment.  The pip command must be run from inside the nspyre folder (where the setup.py script is located). Additionally, some part of this install may require the shell to be started with admin rigths:
```
conda create -n nspyre python = 3
activate nspyre
conda install pyzmq
pip install -e .
```
