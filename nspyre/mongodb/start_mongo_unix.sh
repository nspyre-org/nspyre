#!/bin/bash

# script for starting the mongodb server

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
DB1_PORT=27017
DB2_PORT=27018
REPLSET=NSpyreSet
OPLOG=1024

DB_DATA_NAME=db_files
DB_DATA_BACKUP_NAME=$DB_DATA_NAME"_backup"

DBDATA_DIR=$THIS_DIR/$DB_DATA_NAME
DBDATA_BACKUP_DIR=$THIS_DIR/$DB_DATA_BACKUP_NAME
DB1_DIR=$DBDATA_DIR/db1
DB2_DIR=$DBDATA_DIR/db2
LOG_DIR=$DBDATA_DIR/logs
DB1_LOG=$LOG_DIR/db1
DB2_LOG=$LOG_DIR/db2

# kill existing mongod instances
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
mv $DBDATA_DIR $DBDATA_BACKUP_DIR"/"$DB_DATA_BACKUP_NAME"_"$i
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
# TODO tail log file instead
# ( tail -f -n0 $DB1_LOG & ) | grep -qE -- '[initandlisten] waiting for connections|[initandlisten] now exiting'
# ( tail -f -n0 $DB2_LOG & ) | grep -qE -- '[initandlisten] waiting for connections|[initandlisten] now exiting'

# only needs to performed for first-time setup
# or if the db1/db2 directories were cleared,
# but no disadvantage to running it anyway
# add both servers to a replica set to allow them to start serving the db
# make db1 be the preferred primary using priorities
mongo --eval "rs.initiate({_id:'${REPLSET}', members:[ \
{_id: 0, host: 'localhost:${DB1_PORT}', priority: 2}, \
{_id: 1, host: 'localhost:${DB2_PORT}', priority: 1}  \
]})"
