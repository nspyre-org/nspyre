rem script for starting the mongodb server

set THIS_DIR=%~dp0
set DB1_PORT=27017
set DB2_PORT=27018
set REPLSET=NSpyreSet
set OPLOG=1024

rem kill existing mongod instances
taskkill /f /im mongod.exe

rem start the db servers
start /b mongod --dbpath %THIS_DIR%db1 --logpath %THIS_DIR%logs\db1 ^
	--bind_ip_all --port %DB1_PORT% --replSet %REPLSET% --oplogSize %OPLOG%
start /b mongod --dbpath %THIS_DIR%db2 --logpath %THIS_DIR%logs\db2 ^
	--bind_ip_all --port %DB2_PORT% --replSet %REPLSET% --oplogSize %OPLOG%

rem only needs to performed for first-time setup
rem or if the db1/db2 directories were cleared,
rem but no disadvantage of running it anyway
rem add both servers to a replica set to allow them to start serving the db
rem make db1 be the preferred primary using priorities
mongo --eval "rs.initiate({_id:'%REPLSET%', members:[ {_id: 0, host: 'localhost:%DB1_PORT%', priority: 2}, {_id: 1, host: 'localhost:%DB2_PORT%', priority: 1}]})"
