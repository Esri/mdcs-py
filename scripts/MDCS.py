# ------------------------------------------------------------------------------
# Copyright 2023 Esri
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ------------------------------------------------------------------------------
# Name: MDCS.py
# Description: This is the main program entry point to MDCS.
# Version: 20230726
# Requirements: ArcGIS 10.1 SP1
# Required Arguments: -i:<config_file>
# Usage: python.exe MDCS.py -c:<Optional:command(s)> -i:<config_file>
# Notes:Type 'python.exe mdcs.py' to display the usage and a list of valid command codes.
# Author: Esri Imagery Workflows team
# ------------------------------------------------------------------------------
#!/usr/bin/env python

import arcpy
import sys
import os
from importlib import reload

solutionLib_path = os.path.dirname(os.path.abspath(__file__))  # set the location to the solutionsLib path
[sys.path.append(x) for x in [solutionLib_path, os.path.join(solutionLib_path, 'SolutionsLog'), os.path.join(solutionLib_path, 'Base')]]
import logger
import solutionsLib  # import Raster Solutions library
import Base
logger = reload(logger)  # ArcGIS Pro PYT EVN requires a reload to clear previous instances.
solutionsLib = reload(solutionsLib)
Base = reload(Base)
from ProgramCheckAndUpdate import ProgramCheckAndUpdate
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
redacting_patterns = ["token", 'validatingToken']
# cli callback ptrs
g_cli_callback = None
g_cli_msg_callback = None
# ends
Enabled = "enabled"
StatusKey = "__status"

# cli arcpy callback


def register_for_callbacks(fn_ptr):
    global g_cli_callback
    g_cli_callback = fn_ptr
# ends

# cli msg callback


def register_for_msg_callbacks(fn_ptr):
    global g_cli_msg_callback
    g_cli_msg_callback = fn_ptr
# ends


def postAddData(gdbPath, mdName, info):
    mdName = info['md']
    obvalue = info['pre_AddRasters_record_count']
    fullPath = os.path.join(gdbPath, mdName)

    mosaicMDType = info['type'].lower()
    if mosaicMDType == 'source':
        expression = 'OBJECTID >{}'.format(obvalue)
        try:
            fieldName = 'Dataset_ID'
            fieldExist = arcpy.ListFields(fullPath, fieldName)
            if not fieldExist:
                arcpy.AddField_management(fullPath, fieldName, "TEXT", "", "", "50")
            log.Message('Calculating \'Dataset ID\' for the mosaic dataset ({}) with value ({})'.format(mdName, info[fieldName]), log.const_general_text)
            with arcpy.da.UpdateCursor(fullPath, [fieldName], expression) as rows:
                for row in rows:
                    row[0] = info[fieldName]
                    rows.updateRow(row)
        except BaseException:
            log.Message('Err. Failed to calculate \'Dataset_ID\'', log.const_critical_text)
            log.Message(arcpy.GetMessages(), log.const_critical_text)
            return False
    return True


def main(argc, argv):
    if argc < 2:
        # command-line argument codes.
        # -j:MDCS job file
        # -i:config file.
        # -c:command codes
        # -m:mosaic dataset name
        # -s:Source data paths. (as inputs to command (AR).
        # -l:Full path to log file (including file name)
        user_args = \
            [
                r"-m: Mosaic dataset path including GDB and MD name [e.g. c:\WorldElevation.gdb\Portland]",
                "-s: Source data paths. (As inputs to command (AR). -s: can be repeated to add multiple paths",
                "-l: Log file output path [path+file name]",
                "-artdem: Update DEM path in ART file"
            ]
        print("\nMDCS.py v6.0 [20230726]\nUsage: MDCS.py -c:<Optional:command> -i:<config_file>"
              "\n\nFlags to override configuration values,")
        for arg in user_args:
            print(arg)
        print(
            "\nNote: Commands can be combined with '+' to do multiple operations."
            "\nAvailable commands:")
        user_cmds = solutionsLib.Solutions().getAvailableCommands()
        for key in user_cmds:
            print("\t" + key + ' = ' + user_cmds[key]['desc'])
        sys.exit(1)
    base = Base.Base()
    comInfo = {
        'AR': {'cb': postAddData},  # assign a callback function to run custom user code when adding rasters.
        '__user': {}       # key to pass any custom userCode args to other userCode functions that are defined in MDCS_UC.
    }
    if g_cli_callback is not None:
        base.m_cli_callback_ptr = g_cli_callback
    if g_cli_msg_callback is not None:
        base.m_cli_msg_callback_ptr = g_cli_msg_callback
    global log
    log = logger.Logger(base)
    base.setLog(log)
    argIndx = 0
    md_path_ = artdem = config = com = log_folder = code_base = ''
    PathSeparator = ';'
    jobFile = None
    while argIndx < argc:
        (values) = argv[argIndx].split(':')
        if (len(values[0]) < 2 or
            values[0][:1] != '-' and
                values[0][:1] != '#'):
            argIndx += 1
            continue
        exSubCode = values[0][1:len(values[0])].lower()
        subCode = values.pop(0)[1].lower()
        value = ':'.join(values).strip()
        if subCode == 'c':
            com = value.replace(' ', '')  # remove spaces in between.
        elif subCode == 'i':
            config = value
        elif subCode == 'm':
            md_path_ = value
        elif subCode == 's':
            base.m_sources += value + PathSeparator
        elif subCode == 'l':
            log_folder = value
        elif subCode == 'b':
            code_base = value
        elif exSubCode == 'artdem':
            artdem = value
        elif exSubCode == 'gprun':
            log.isGPRun = True                  # direct log messages also to (arcpy.AddMessage)
        elif subCode == 'p':
            pMax = value.rfind('$')
            if pMax == -1:
                pMax = value.rfind('@')
            if pMax == -1:
                argIndx += 1
                continue
            dynamic_var = value[pMax + 1:].upper()
            v = value[0: pMax]
            if dynamic_var.strip() != '':
                if (dynamic_var in base.m_dynamic_params.keys()) is False:
                    base.m_dynamic_params[dynamic_var] = v
        elif exSubCode.startswith('__'):  # prefix to pass custom userCode args.
            comInfo['__user'][exSubCode] = value
        elif subCode == 'j':
            jobFile = value
        argIndx += 1
    if base.m_sources.endswith(PathSeparator):
        base.m_sources = base.m_sources[:len(base.m_sources) - 1]
    if code_base != '':
        base.setCodeBase(code_base)
    if md_path_ != '':
        (p, f) = os.path.split(md_path_)
        f = f.strip()
        const_gdb_ext_len_ = len(base.const_geodatabase_ext)
        ext = p[-const_gdb_ext_len_:].lower()
        if ((ext == base.const_geodatabase_ext.lower() or
             ext == base.const_geodatabase_SDE_ext.lower()) and
                f != ''):
            p = p.replace('\\', '/')
            w = p.split('/')
            workspace_ = ''
            for i in range(0, len(w) - 1):
                workspace_ += w[i] + '/'
            gdb_ = w[len(w) - 1]
            base.m_workspace = workspace_
            base.m_geodatabase = w[len(w) - 1]
            base.m_mdName = f
    configName, ext = os.path.splitext(config)
    configName = os.path.basename(configName)
    # setup log
    log.Project('MDCS')
    log.LogNamePrefix(configName)
    log.StartLog()
    log_output_folder = os.path.join(os.path.dirname(solutionLib_path), 'logs')
    if log_folder != '':
        (path, fileName) = os.path.split(log_folder)
        if path != '':
            log_output_folder = path
        if fileName != '':
            log.LogFileName(fileName)
    log.SetLogFolder(log_output_folder)
    # ends
    # Source version check.
    versionCheck = ProgramCheckAndUpdate()
    log.Message('Checking for updates..', logger.Logger.const_general_text)
    verMessage = versionCheck.run(solutionLib_path)
    if verMessage is not None:
        if verMessage is True:
            log.Message('Installed version is the latest version', logger.Logger.const_general_text)
        else:
            if verMessage != 'Ignore':
                log.Message(verMessage, logger.Logger.const_warning_text)
    # ends
    if (config and
            os.path.isfile(config) is False):
        log.Message('Input config file is not specified/not found! ({})'.format(config), logger.Logger.const_critical_text)
        log.Message(base.CCMD_STATUS_FAILED, logger.Logger.const_status_text)    # set (failed) status
        log.WriteLog('#all')
        return False
    if artdem != '':
        (base.m_art_ws, base.m_art_ds) = os.path.split(artdem)
        base.m_art_apply_changes = True
    if com == '':
        com = base.const_cmd_default_text
    try:
        logging_items = []
        for item in argv:
            if '$' not in item:
                logging_items.append(item)
                continue
            value, key = item.split('$')
            if key not in redacting_patterns:
                logging_items.append(item)
            else:
                logging_items.append('REDACTED$' + key)
        inarg = '||'.join([str(item) for item in logging_items])
        log.Message("Input arguments {}".format(inarg), log.const_general_text)
    except BaseException:
        print("Failed to print input arguments")
    if jobFile:
        params = {}
        with open (jobFile) as reader:
            try:
                payload = json.load(reader)
            except Exception as e:
                print (f'{e}')
                return False
        params["payload"] = payload
        params['__mdcs__'] = {}
        worker(**params)
        results = params['__mdcs__']['resp']
    else:
        results = runWorkflow (base, config, com, comInfo)
    log.Message("Done...", log.const_general_text)
    log.WriteLog('#all')  # persist information/errors collected.
    return results

def runMDCS(argv):
    print("** loading arcpy ***")
    import MDCS
    ret = MDCS.main(len(argv), argv)
    return ret

def runWorkflow(base, config, com, comInfo):
    from importlib import reload
    import solutionsLib  # import Raster Solutions library
    solutionsLib = reload(solutionsLib)
    solutions = solutionsLib.Solutions(base)
    results = solutions.run(config, com, comInfo)
    return results

def worker(**params):
    payload = params["payload"]
    captureMsg = CaptureMessages()
    job = payload
    if job is None:
        captureMsg.addMessage("Job empty!")
        captureMsg.status = False
        return captureMsg
    try:
        if "job" not in job and "params" not in job["job"]:
            captureMsg.addMessage("job/params not found!")
            captureMsg.status = False
            return captureMsg
        args = dict.copy(job["job"]["params"])
        usrOutput = args["output"]
        if "build" not in args:
            captureMsg.addMessage("input/MDCS|build entry not found!")
            captureMsg.status = False
            return captureMsg
        initStruct = None
        if "build" not in args:
            mdcs = {"steps": [initStruct]}
        else:
            if "steps" not in args["build"]:
                captureMsg.addMessage("input/build/steps entry not found!")
                captureMsg.status = False
                return captureMsg
            mdcs = args["build"]
            if initStruct:
                mdcs["steps"].insert(0, initStruct)
        steps = mdcs["steps"]
        # early check on steps schema/format to bail out early.
        for step in steps:
            if any(s not in step for s in [Enabled, "id"]):
                raise Exception("Step key (enabled, id) must be specified.")
        hstCleanUpRoot = os.path.dirname(solutionLib_path)
        hstRootMd = os.path.join(hstCleanUpRoot, "output")
        # }.
        # call step-functions
        stepInfo = StepInfoMDCS()
        stepInfo.init(
            **{
                "@output": os.path.join(hstRootMd, usrOutput["path"]),
                "@payload": os.path.join(hstCleanUpRoot, "payload"),
                "@wp": hstCleanUpRoot,
            }
        )
        lclMdPath = os.path.join(hstRootMd, "undefined.gdb")
        stepStatus = False
        for step in steps:  # will always have the def 'root' step.
            sId = step["id"]
            if not getBooleanValue(step[Enabled]):
                captureMsg.addMessage(f"Skipping step ({sId})")
                continue
            sType = step["type"].lower()
            if sType == "mdcs":
                mdcs = step["args"]
                # To facilitate AID MDCS custom user function writers to access the def MDCSPOD work Path.
                mdcs["__wp__"] = hstCleanUpRoot
                mdcs["__step__"] = sId  # step Id
                mdcs["__job__"] = payload["job"]["id"]  # AID job Id
                updInput = stepInfo.addInput(sId, mdcs)
                retVals, stepStatus = doWork(usrOutput, hstCleanUpRoot, updInput[sId], captureMsg, **params)
                stepInfo.addResults(sId, retVals)
                if not stepStatus:
                    break
                for cmd in retVals:
                    if "output" in cmd:
                        lclMdPath = cmd["output"]
                stepInfo.addResults(sId, retVals)
        params[StatusKey] = {"mdcs": {}}
        params[StatusKey]["mdcs"] = {"retVals": stepInfo.getStepResults(), "status": stepStatus}
        if not stepStatus:
            raise Exception(f"MDCS/step({sId}) failed!")
        # prevent illegal uploads outside of the host MDCS workfolder root, but
        # allow for URLs/online references to pass through.
        if isinstance(lclMdPath, str) and not lclMdPath.startswith(hstCleanUpRoot) and os.path.exists(lclMdPath):
            raise Exception("MDCS/steps/(output) is invalid/omitted/empty!")
        # skip if upload to a cloud-store is not needed, for e.g. when user
        # function's last command is to publish as a service.
        if (Enabled in usrOutput and not getBooleanValue(usrOutput[Enabled])) or Enabled not in usrOutput:
            captureMsg.addMessage("Cloud-upload has been disabled in the request, skipping..")
            captureMsg.status = True  # not an error if disabled.
            return captureMsg
        # ends
    except Exception as e:
        captureMsg.status = False
        captureMsg.addMessage(f"Err. {e}")
    return captureMsg

class CaptureMessages(object):
    def __init__(self):
        self.response = {"logs": [], "status": False}
        self._zip = None

    def addMessage(self, msg, code=0, printToConsole=True):
        if msg is None:
            return False
        log = "{}".format(msg)
        if printToConsole:
            print(log)
        self.response["logs"].append(log)
        return True

    def getMessages(self):
        return self.response

    @property
    def status(self):
        return self.response["status"]

    @status.setter
    def status(self, value):
        self.response["status"] = value

    @property
    def zip(self):
        return self._zip

    @zip.setter
    def zip(self, value):
        self._zip = value

    def write(self, output):
        try:
            folder = os.path.dirname(output)
            os.makedirs(folder, exist_ok=True)
            with open(output, "wb") as writer:
                [writer.write(bytes(f"{msg}\n", "utf-8")) for msg in self.response["logs"]]
        except Exception as e:
            self.addMessage(f"Err. {e}")
            return False
        return True

    def __add__(self, obj):
        if not isinstance(obj, CaptureMessages):
            return self
        self.response["logs"] += obj.response["logs"]
        self.response["status"] = obj.response["status"]
        self._zip = obj._zip
        return self

def doWork(usrOutput, hstCleanUpRoot, mdcs, captureMsg, **kwargs):  # returns an array
    try:
        rootLogs = hstCleanUpRoot
        writeToPath = hstCleanUpRoot
        validKeys = ["i", "m", "c", "p", "s"]
        mustKeys = ["c"]
        mapToHost = ["i", "s"]
        keys = mdcs.keys()
        if any(s not in validKeys and not s.startswith("__") for s in keys):
            raise Exception(f"Err. Invalid/non-implemented flag found!\nValid flags are {validKeys}")
        if any(s not in keys for s in mustKeys):
            raise Exception(f"Err. The following flags must exist in the payload,\n{mustKeys}")
        # invoke MDCS {
        for flag in mapToHost:
            if flag in mdcs:
                mdcs[flag] = os.path.join(writeToPath, mdcs[flag])
        mdcs["b"] = os.path.join(os.path.dirname(__file__), 'Base')      # -b is positioned at the /Base root as MDCS modules get
        mdcs["l"] = os.path.join(rootLogs, "logs/")             # addressed using ../../ relative to Base module path.
        if "m" in mdcs:
            if not mdcs["m"]:
                raise Exception("Err. MDCS/steps/args/m is not set.")
            hstRootMd = os.path.join(hstCleanUpRoot, "output")
            hstMd = os.path.join(os.path.join(hstRootMd, usrOutput["path"]), mdcs["m"])
            mdcs["m"] = hstMd
        # invoke MDCS
        argv = []
        content = mdcs
        for flag, value in content.items():
            if not isinstance(value, list):
                value = [value]
            for i, v in enumerate(value):
                argv.append(f"-{flag}:{v}")
        captureMsg.addMessage("Invoking MDCS..")
        Log_Workers = 1
        results = []
        with ProcessPoolExecutor(max_workers=Log_Workers) as executor:
            tasks = {executor.submit(
                runMDCS, argv)}
            for task in as_completed(tasks):
                try:
                    results = task.result()
                    print(
                        f'Response> {results}')
                except Exception as e:
                    raise Exception(f'Err. {e}') from e
        kwargs['__mdcs__']['resp'] = results
        response = json.dumps(results)
        served = bytes(response, "utf8")
        respVals = json.loads(served)
        if not respVals:
            return respVals, False
        status = True
        if (
            "value" in respVals[-1]
            and getBooleanValue(  # hotfix (to revisit later to remove code) # GH https://github.com/ArcGIS/AID/issues/4758
                respVals[-1]["value"]
            )
            and "output" in respVals[-1]
        ):
            return respVals, status
        if False in [s["value"] for s in respVals]:
            status = False
        return respVals, status
    except Exception as e:
        captureMsg.addMessage(f"Err. doWork/{e}")
    return [], False


class StepInfoMDCS():
    def __init__(self):
        pass

    def init(self, **kwargs):
        self._stepResult = {}
        self._stepInput = {}
        self._stepId = None
        self._kwargs = kwargs

    def addInput(self, sId, sInput, **kwargs):
        if sInput is None or sId is None or not isinstance(sInput, dict):
            return None
        self._stepId = sId
        self._stepInput[self._stepId] = sInput
        for k in sInput:
            if isinstance(sInput[k], str) and sInput[k].startswith("@"):
                self._stepInput[self._stepId][k] = self.getResults(sInput[k])
            elif isinstance(sInput[k], list):
                for i in range(0, len(sInput[k])):
                    if sInput[k][i].startswith("@"):
                        value, key = sInput[k][i].split("$")
                        self._stepInput[self._stepId][k][i] = f"{self.getResults(value)}${key}"
        return self._stepInput

    def addResults(self, sId, stepVals):
        if sId not in self._stepInput:
            return False
        self._stepResult[sId] = stepVals
        return True

    def getResults(self, key):
        if key is None or not key.startswith("@"):
            return None
        subs = key[1:].split("/")
        nSubs = len(subs)
        if f"@{subs[0]}" in self._kwargs:  # is internal lookup command? e.g. @output
            sId = subs[0]
            subs[0] = self._kwargs[f"@{subs[0]}"]
            value = "/".join(subs)
            return value
        if nSubs < 3:  # id/dir/key
            return None
        sId, sDir, sKey = subs[0], subs[1], subs[2]
        if sDir not in ["i", "o"]:
            return None
        if sKey == "p" and nSubs < 4:  # id/dir/key/param
            return None
        if sDir == "i":
            if sId in self._stepInput and sKey in self._stepInput[sId]:
                if sKey == "p":
                    for it in self._stepInput[sId][sKey]:
                        if it.endswith(f"${subs[-1]}"):
                            return it.split("$")[0]
                    return None
                return self._stepInput[sId][sKey]
            return None
        if sId not in self._stepResult:
            return None
        steps = self._stepResult[sId]
        if not isinstance(steps, list):
            return None
        value = None
        for step in steps:
            if "cmd" not in step:
                continue
            if step["cmd"] == sKey:
                value = step["output"] if "output" in step else None
                break
        return value

    def getStepResults(self):
        return self._stepResult


def getBooleanValue(value):
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    val = value
    if not isinstance(val, str):
        val = str(val)
    val = val.lower()
    if val in ['true', 'yes', 't', '1', 'y']:
        return True
    return False

if __name__ == '__main__':
    main(len(sys.argv), sys.argv)
