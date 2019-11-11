:-------------------------------------
REM  --> Check for permissions
    IF "%PROCESSOR_ARCHITECTURE%" EQU "amd64" (
>nul 2>&1 "%SYSTEMROOT%\SysWOW64\cacls.exe" "%SYSTEMROOT%\SysWOW64\config\system"
) ELSE (
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
)

REM --> If error flag set, we do not have admin.
if '%errorlevel%' NEQ '0' (
    echo Requesting administrative privileges...
    goto UACPrompt
) else ( goto gotAdmin )

:UACPrompt
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    set params= %*
    echo UAC.ShellExecute "cmd.exe", "/c ""%~s0"" %params:"=""%", "", "runas", 1 >> "%temp%\getadmin.vbs"

    "%temp%\getadmin.vbs"
    del "%temp%\getadmin.vbs"
    exit /B

:gotAdmin
    pushd "%CD%"
    CD /D "%~dp0"
:--------------------------------------   
net stop MongoDB
net stop MongoDB1
net stop MongoDB2

mkdir C:\mongodb
mkdir C:\mongodb\db1
mkdir C:\mongodb\db2
mkdir C:\mongodb\log

copy /Y mongodb1.cfg C:\mongodb\mongodb1.cfg
copy /Y mongodb2.cfg C:\mongodb\mongodb2.cfg

mongod --config C:\mongodb\mongodb1.cfg --serviceName MongoDB1 --serviceDisplayName MongoDB1 --install
mongod --config C:\mongodb\mongodb2.cfg --serviceName MongoDB2 --serviceDisplayName MongoDB2 --install

start_mongodb.bat