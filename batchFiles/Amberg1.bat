@echo off
echo Calling MDCS for Amberg1.
set MDCS_INST_ROOT=c:\Image_Mgmt_Workflows\GitForWindows\mdcs-py
set MDCS_CFG_FILE=%MDCS_INST_ROOT%\Parameter\Config\Amberg1.xml
echo Output will be placed at %MDCS_INST_ROOT%md as referenced by the node "<WorkspacePath>" in the config file %MDCS_CFG_FILE%
python.exe %MDCS_INST_ROOT%\Scripts\mdcs.py -i:%MDCS_CFG_FILE%
pause
