rem script for starting the mongodb server

set THIS_DIR=%~dp0
rem mongod (daemon) port numbers to use
set DB1_PORT=27017
set DB2_PORT=27018
rem mongo replicate set name
set REPLSET=NSpyreSet
rem max mongo operation log length (MB)
set OPLOG=1024

rem database file locations

set DB_DATA_NAME=db_files
set DB_DATA_BACKUP_NAME=%DB_DATA_NAME%_backup

set DBDATA_DIR=%THIS_DIR%%DB_DATA_NAME%
set DBDATA_BACKUP_DIR=%THIS_DIR%%DB_DATA_BACKUP_NAME%
set DB1_DIR=%DBDATA_DIR%\db1
set DB2_DIR=%DBDATA_DIR%\db2
set LOG_DIR=%DBDATA_DIR%\logs
set DB1_LOG=%LOG_DIR%\db1
set DB2_LOG=%LOG_DIR%\db2

rem max time (s) to wait for the mongod instances to start and elect a primary
set TIMEOUT=60

rem kill existing mongod instances
echo "killing mongodb daemons..."
taskkill /t /f /im mongod.exe

rem allow time for mongod to release access to db files
SLEEP 2

rem move dbs and logs to backup folder
echo "removing database files..."
rem make the backups directory if it doesn't exist
if not exist %DBDATA_BACKUP_DIR% mkdir %DBDATA_BACKUP_DIR%
rem find a number to append to the db files directory
set i=0
:while
if exist %DBDATA_BACKUP_DIR%/%DB_DATA_BACKUP_NAME%_%i% (
    set /a i=%i%+1
    goto :while
)
rem move the current db files to the backup folder
if exist %DBDATA_DIR% (
	move %DBDATA_DIR% %DBDATA_BACKUP_DIR%/%DB_DATA_BACKUP_NAME%_%i%
)
rem make new folders for the db files
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

rem add both servers to a replica set to allow them to start serving the db
rem make db1 be the preferred primary using priorities
mongo --eval "rs.initiate({_id:'%REPLSET%', members:[ {_id: 0, host: 'localhost:%DB1_PORT%', priority: 2}, {_id: 1, host: 'localhost:%DB2_PORT%', priority: 1}]})"

for /l %i in (1, 1, %TIMEOUT%) do (
    rem if running rs.status() on the mongo console contains "PRIMARY" then
    rem the election process has succeeded and mongodb is now running
    mongo --eval "rs.status()" | findstr "PRIMARY"
    if %ERRORLEVEL% EQU 0 (
        goto :end_rs_status_loop
    )
    SLEEP 1
)
:end_rs_status_loop

if %i% NEQ %TIMEOUT% (
    echo "mongodb started successfully..."
) else (
	echo "ERROR: timed out waiting for mongod to start..."
	exit /b 1
)
