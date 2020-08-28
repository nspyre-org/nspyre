#!/bin/bash

# script for starting the mongodb server

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
DB1_PORT=27017
DB2_PORT=27018
REPLSET=NSpyreSet
OPLOG=1024

DBDATA_DIR=$THIS_DIR/db_files
DB1_DIR=$DBDATA_DIR/db1
DB2_DIR=$DBDATA_DIR/db2
LOG_DIR=$DBDATA_DIR/logs
DB1_LOG=$LOG_DIR/db1
DB2_LOG=$LOG_DIR/db2

# kill existing mongod instances
killall mongod

# allow time for mongod to release ports
sleep 2

# remove dbs and logs
rm -rf $DBDATA_DIR
mkdir $DBDATA_DIR
mkdir $DB1_DIR
mkdir $DB2_DIR
mkdir $LOG_DIR

# start the db servers
mongod --dbpath $DB1_DIR --logpath $DB1_LOG --bind_ip_all \
		--port $DB1_PORT --replSet $REPLSET --oplogSize $OPLOG --fork
mongod --dbpath $DB2_DIR --logpath $DB2_LOG --bind_ip_all \
		--port $DB2_PORT --replSet $REPLSET --oplogSize $OPLOG --fork

# allow time for mongod to start
sleep 2
# TODO tail log file instead
# ( tail -f -n0 $DB1_LOG & ) | grep -qE -- '[initandlisten] waiting for connections|[initandlisten] now exiting'
# ( tail -f -n0 $DB2_LOG & ) | grep -qE -- '[initandlisten] waiting for connections|[initandlisten] now exiting'

# only needs to performed for first-time setup
# or if the db1/db2 directories were cleared,
# but no disadvantage of running it anyway
# add both servers to a replica set to allow them to start serving the db
# make db1 be the preferred primary using priorities
mongo --eval "rs.initiate({_id:'${REPLSET}', members:[ \
{_id: 0, host: 'localhost:${DB1_PORT}', priority: 2}, \
{_id: 1, host: 'localhost:${DB2_PORT}', priority: 1}  \
]})"
