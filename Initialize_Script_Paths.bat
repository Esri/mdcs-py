@echo off
set var=%cd%

rem This batch file will initialize the ArcGIS version number the sample files.
rem It will also set the current folder as the working folder in the batch files and script files. 

IF EXIST c:\python27\arcgis10.1\python.exe (

set id=10.1
goto :RunReplace
) 

IF EXIST c:\python27\arcgis10.2\python.exe (

set id=10.2
goto :RunReplace

)
IF EXIST c:\python27\arcgis10.3\python.exe (

set id=10.3
goto :RunReplace
) 

IF EXIST c:\python27\arcgis10.4\python.exe (

set id=10.4
goto :RunReplace

)
goto :ShowError

:RunReplace
c:\python27\arcgis%id%\python.exe %var%\scripts\search_replace.py %var%\batchFiles arcgisVer arcgis%id% *.bat
c:\python27\arcgis%id%\python.exe %var%\scripts\search_replace.py %var%\batchFiles currFolder %var% *.bat
c:\python27\arcgis%id%\python.exe %var%\scripts\search_replace.py %var%\Parameter\Config currFolder %var% *.xml

copy /y nul Reset_Script_Paths.bat
echo @echo off
echo @echo This batch file was automatically created after successfully executing Intialize_Script_Paths.bat. >Reset_Script_Paths.bat
echo. >>Reset_Script_Paths.bat
echo @echo This batch file will reset the ArcGIS version number and current folder location to be used by the Sample files. >>Reset_Script_Paths.bat
echo @echo The batch files will be reset to the state when you first downloaded the batch file. >>Reset_Script_Paths.bat
echo @echo Type Ctrl + C to cancel execution. >>Reset_Script_Paths.bat  
echo pause >>Reset_Script_Paths.bat  
echo. >>Reset_Script_Paths.bat  
echo c:\python27\arcgis%id%\python.exe %var%\scripts\search_replace.py %var%\batchFiles arcgis%id% arcgisVer *.bat >>Reset_Script_Paths.bat
echo. >>Reset_Script_Paths.bat
echo c:\python27\arcgis%id%\python.exe %var%\scripts\search_replace.py %var%\batchFiles %var% currFolder *.bat >>Reset_Script_Paths.bat
echo. >>Reset_Script_Paths.bat
echo c:\python27\arcgis%id%\python.exe %var%\scripts\search_replace.py %var%\Parameter\Config %var% currFolder *.xml >>Reset_Script_Paths.bat
echo pause >>Reset_Script_Paths.bat  

ECHO "Successfully set ArcGIS version number to %id%."
ECHO "Successfully set sample paths to %var%."
goto :endofbatch 

:ShowError
ECHO "ERROR: Could not find Python Install Location in C:\python27\"

:endofbatch
pause
