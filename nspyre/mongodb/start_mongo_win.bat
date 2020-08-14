rem script for starting the mongodb server

set THIS_DIR=%~dp0
set DB1_PORT=27017
set DB2_PORT=27018
set REPLSET=NSpyreSet
set OPLOG=1024

set DBDATA_DIR=%THIS_DIR%db_files
set DB1_DIR=%DBDATA_DIR%\db1
set DB2_DIR=%DBDATA_DIR%\db2
set LOG_DIR=%DBDATA_DIR%\logs
set DB1_LOG=%LOG_DIR%\db1
set DB2_LOG=%LOG_DIR%\db2

rem kill existing mongod instances
taskkill /t /f /im mongod.exe

rem remove dbs and logs
del /s /q %DBDATA_DIR%
mkdir %DBDATA_DIR%
mkdir %DB1_DIR%
mkdir %DB2_DIR%
mkdir %LOG_DIR%

rem start the db servers
start /b mongod --dbpath %DB1_DIR% --logpath %DB1_LOG% ^
	--bind_ip_all --port %DB1_PORT% --replSet %REPLSET% --oplogSize %OPLOG%
start /b mongod --dbpath %DB2_DIR% --logpath %DB2_LOG% ^
	--bind_ip_all --port %DB2_PORT% --replSet %REPLSET% --oplogSize %OPLOG%

rem allow time for mongod to start
SLEEP 2

rem only needs to performed for first-time setup
rem or if the db1/db2 directories were cleared,
rem but no disadvantage of running it anyway
rem add both servers to a replica set to allow them to start serving the db
rem make db1 be the preferred primary using priorities
mongo --eval "rs.initiate({_id:'%REPLSET%', members:[ {_id: 0, host: 'localhost:%DB1_PORT%', priority: 2}, {_id: 1, host: 'localhost:%DB2_PORT%', priority: 1}]})"
