#!/bin/bash

# script for starting the mongodb server

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
# mongod (daemon) port numbers to use
DB1_PORT=27017
DB2_PORT=27018
# mongo replicate set name
REPLSET=NSpyreSet
# max mongo operation log length (MB)
OPLOG=1024

# database file locations
DB_DATA_NAME=db_files
DB_DATA_BACKUP_NAME=$DB_DATA_NAME"_backup"

DBDATA_DIR=$THIS_DIR/$DB_DATA_NAME
DBDATA_BACKUP_DIR=$THIS_DIR/$DB_DATA_BACKUP_NAME
DB1_DIR=$DBDATA_DIR/db1
DB2_DIR=$DBDATA_DIR/db2
LOG_DIR=$DBDATA_DIR/logs
DB1_LOG=$LOG_DIR/db1
DB2_LOG=$LOG_DIR/db2

# max time (s) to wait for the mongod instances to start and elect a primary
TIMEOUT=60

# kill any existing mongod instances
echo "killing mongodb daemons..."
killall -q mongod

# allow time for mongod to release ports
sleep 2

# move dbs and logs to backup folder
echo "removing database files..."
# make the backups directory if it doesn't exist
if [ ! -d $DBDATA_BACKUP_DIR ]; then
	mkdir $DBDATA_BACKUP_DIR
fi
# find a number to append to the db files directory
i="0"
while [ -d $DBDATA_BACKUP_DIR"/"$DB_DATA_BACKUP_NAME"_"$i ]; do
	i=$((i+1))
done
# move the current db files to the backup folder
if [ -d $DBDATA_DIR ]; then
	mv $DBDATA_DIR $DBDATA_BACKUP_DIR"/"$DB_DATA_BACKUP_NAME"_"$i
fi
# make new folders for the db files
mkdir $DBDATA_DIR
mkdir $DB1_DIR
mkdir $DB2_DIR
mkdir $LOG_DIR

# start the db servers
echo "starting mongodb daemons..."
mongod --dbpath $DB1_DIR --logpath $DB1_LOG --bind_ip_all \
		--port $DB1_PORT --replSet $REPLSET --oplogSize $OPLOG --fork
mongod --dbpath $DB2_DIR --logpath $DB2_LOG --bind_ip_all \
		--port $DB2_PORT --replSet $REPLSET --oplogSize $OPLOG --fork

# allow time for mongod to start
sleep 2

# add both servers to a replica set to allow them to start serving the db
# make db1 be the preferred primary using priorities
mongo --eval "rs.initiate({_id:'${REPLSET}', members:[ \
{_id: 0, host: 'localhost:${DB1_PORT}', priority: 2}, \
{_id: 1, host: 'localhost:${DB2_PORT}', priority: 1}  \
]})"

# wait for mongod to elect a primary and be ready for calls
for i in $(seq 1 1 $TIMEOUT); do
	# if running rs.status() on the mongo console contains "PRIMARY" then
	# the election process has succeeded and mongodb is now running
	mongo --eval "rs.status()" | grep "PRIMARY"
	if [ $? -eq 0 ]; then
		break
	fi
	sleep 1.0
done

if [ $i -ne $TIMEOUT ]; then
	echo "mongodb started successfully..."
else
	echo "ERROR: timed out waiting for mongod to start..."
	exit 1
fi
