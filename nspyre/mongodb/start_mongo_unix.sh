#!/bin/bash

# may be required to start the mongodb daemon
#systemctl start mongodb.service

# start the db servers
mongod --config mongodb1_unix.cfg --fork
mongod --config mongodb2_unix.cfg --fork

# only needs to performed for first-time setup 
# or if the db1/db2 directories were cleared
# add both servers to a replica set to allow them to start serving the db
# TODO use same port as specificed in .cfg
mongo --eval "rs.initiate({_id:'NSpyreSet', members:[ \
{_id: 0, host: 'localhost:27017'}, \
{_id: 1, host: 'localhost:27018'}  \
]})"
