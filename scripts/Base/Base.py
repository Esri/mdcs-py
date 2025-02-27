# ------------------------------------------------------------------------------
# Copyright 2025 Esri
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
# Name: Base.py
# Description: Base class used by MDCS/All Raster Solutions components.
# Version: 20250220
# Requirements: ArcGIS 10.1 SP1
# Author: Esri Imagery Workflows team
# ------------------------------------------------------------------------------
#!/usr/bin/env python

import os
import sys
import arcpy
try:
    if (sys.version_info[0] < 3):           # _winreg has been renamed as (winreg) in python3+
        from _winreg import *
    else:
        from winreg import *
except ImportError as e:
    print('winreg support is disabled!\n{}'.format(e))
from datetime import datetime
from defusedxml import minidom
from inspect import signature
mdcs_uc_error = None
try:
    import MDCS_UC
    from importlib import reload
    MDCS_UC = reload(MDCS_UC)  # ArcGIS Pro PYT EVN requires a reload to clear previous instances.
except Exception as e:
    mdcs_uc_error = e
    print(f'User-Code functions disabled.\n{e}')
try:
    from arcpy.ia import *
    arcpy.CheckOutExtension("ImageAnalyst")
except BaseException:
    print('arcpy.ia is not available.')


class DynaInvoke:
    # log status types enums
    const_general_text = 0
    const_warning_text = 1
    const_critical_text = 2
    const_status_text = 3
    # ends

    def __init__(self, name, args, evnt_fnc_update_args=None, log=None):
        self.m_name = name
        self.m_args = args
        self.m_evnt_update_args = evnt_fnc_update_args
        self.m_log = log
        self._sArgs = []

    def _message(self, msg, msg_type):
        if (self.m_log):
            return self.m_log(msg, msg_type)
        print(msg)

    def init(self, **kwargs):
        self.fnc_ptr = None
        if ('sArgs' in kwargs):
            self._sArgs = kwargs['sArgs']
            if (isinstance(self._sArgs, list)):
                if (self._sArgs):
                    if (isinstance(self._sArgs[0], list)):
                        self._sArgs = self._sArgs[0]        # handles only 1 sub method on the parent object for now.
                        # sub args to use in a method of the main function object. e.g. X = a->fn1(args) X->fn2(sargs)
        try:
            nspce = self.m_name.split(".")
            cls = nspce.pop()
            self.fnc_ptr = getattr(sys.modules[".".join(nspce)], cls)
            arg_count = len(signature(self.fnc_ptr).parameters)
        except Exception as exp:
            self._message(str(exp), self.const_critical_text)
            return False
        len_args = len(self.m_args)
        if (len_args < arg_count):
            # self._message('Args less than required, filling with default (#)', self.const_warning_text)
            for i in range(len_args, arg_count):
                self.m_args.append('#')
        elif (len_args > arg_count):
            ##            self._message('More args supplied than required to function (%s)' % (self.m_name), self.const_warning_text)
            self.m_args = self.m_args[:arg_count]
        return True

    def invoke(self):   # chs
        result = 'OK'
        try:
            if self.fnc_ptr is None:
                raise Exception(f'{self.__class__.__name__}/Not initialized.')
            if (self.m_evnt_update_args is not None):
                usr_args = self.m_evnt_update_args(self.m_args, self.m_name)
                if (usr_args is None):      # set to (None) to skip fnc invocation, it's treated as a non-error.
                    return True
                if (usr_args is not None and
                        len(usr_args) == len(self.m_args)):      # user is only able to update the contents, not to trim or expand args.
                    ##                    self._message('Original args may have been updated through custom code.', self.const_warning_text)
                    self.m_args = usr_args
            self._message('Calling (%s)' % (self.m_name), self.const_general_text)
            ret = self.fnc_ptr(*self.m_args)    # gp-tools return NULL?
            if (self._sArgs):
                fn = self._sArgs.pop(0)
                if (hasattr(ret, fn)):
                    self.fnc_ptr = getattr(ret, fn)
                    ret = self.fnc_ptr(*self._sArgs)
            return True
        except Exception as exp:
            result = 'FAILED'
            self._message(str(exp), self.const_critical_text)
            return False
        finally:
            self._message('Status: %s' % (result), self.const_general_text)


class Base(object):

    # begin - constansts
    const_general_text = 0
    const_warning_text = 1
    const_critical_text = 2
    const_status_text = 3

    const_cmd_default_text = "#defaults"
    const_geodatabase_ext = '.GDB'
    const_geodatabase_SDE_ext = '.SDE'

    # base init codes. (const_strings)
    const_init_ret_version = 'version'
    const_init_ret_sde = 'sde'
    const_init_ret_patch = 'patch'
    # ends

    # version specific
    const_ver_len = 4

    CMAJOR = 0
    CMINOR = 1
    CSP = 2
    CBUILD = 3
    CVERSION_ATTRIB = 'version'

    # ends

    # externally user defined functions specific
    CCLASS_NAME = 'UserCode'
    CMODULE_NAME = 'MDCS_UC'
    # ends

    # log status (codes)
    CCMD_STATUS_OK = 'OK'
    CCMD_STATUS_FAILED = 'Failed!'
    # ends

    NODE_TYPE_TEXT = 3
    NODE_TYPE_ELEMENT = 1

    EVT_ON_START = "_OnStart"
    EVT_ON_EXIT = "_OnExit"
    # ends

    def __init__(self):
        self.m_log = None
        self.m_doc = None

        # the follwoing variables could be overridden by the command-line to replace respective values in XML config file.
        self.m_workspace = ''
        self.m_geodatabase = ''
        self.m_mdName = ''  # mosaic dataset name.
        # ends

        self.m_sources = ''

        self.m_gdbName = ''
        self.m_geoPath = ''
        self.m_config = ''
        self.m_commands = ''

        self.m_sources = ''  # source data paths for adding new rasters.

        self.m_dynamic_params = {}

        # art file update specific variables
        self.m_art_apply_changes = ''
        self.m_art_ws = ''
        self.m_art_ds = ''
        # ends

        # To keep track of the last objectID before any new data items could be added.
        self.m_last_AT_ObjectID = 0  # by default, take in all the previous records for any operation.

        # SDE specific variables
        self.m_IsSDE = False
        self.m_SDE_database_user = ''
        # ends

        # set MDCS code base path
        self.m_code_base = ''
        self.setCodeBase(os.path.dirname(__file__))
        # ends

        # client_callback_ptrs
        self.m_cli_callback_ptr = None
        self.m_cli_msg_callback_ptr = None
        # ends
        self.m_userClassInstance = None
        self.m_data = None
        self.on_evnt_args = [self.EVT_ON_START, self.EVT_ON_EXIT]

    def init(self):  # return (status [true|false], reason)
        self.m_data = {
            'log': self.m_log,
            'mdcs': self.m_doc,
            'base': self    # pass in the base object to allow access to common functions.
        }
        try:
            frame = sys._getframe(0).f_globals
            module = frame[self.CMODULE_NAME]
            self.m_userClassInstance = getattr(module, self.CCLASS_NAME)(self.m_data)
        except BaseException:
            error_msg = '{}/{} not found. Users commands disabled!'.format(self.CMODULE_NAME, self.CCLASS_NAME)
            error_msg = (error_msg + ' User code error: {}'.format(mdcs_uc_error)) if mdcs_uc_error else error_msg
            self.log(error_msg, self.const_warning_text)
        if (self.m_doc is None):
            return (True, 'UserCode only')
        # version check.
        try:
            # Update in memory parameter DOM to reflect {-m} user values
            if (self.m_workspace):
                self.setXMLNodeValue('Application/Workspace/WorkspacePath', 'WorkspacePath', self.m_workspace, '', '')
            if (self.m_geodatabase):
                self.setXMLNodeValue('Application/Workspace/Geodatabase', 'Geodatabase', self.m_geodatabase, '', '')
            if (self.m_mdName):
                self.setXMLNodeValue('Application/Workspace/MosaicDataset/Name', 'Name', self.m_mdName, '', '')
            # ends
            min = [int(x) if x else 0 for x in self.getXMLXPathValue("Application/ArcGISVersion/Product/Min", "Min").split('.')]
            max = [int(x) if x else 0 for x in self.getXMLXPathValue("Application/ArcGISVersion/Product/Max", "Max").split('.')]
            if not sum(min):
                min = [0] * self.const_ver_len
            if not sum(max):
                max = [0] * self.const_ver_len
            if (self.CheckMDCSVersion(min, max) is False):
                return (False, self.const_init_ret_version)  # version check failed.
        except Exception as inst:
            self.log(f'{inst}', self.const_critical_text)
            return (False, self.const_init_ret_version)
        # ends
        # ArcGIS patch test.
        if (self.isArcGISPatched() == False):
            self.log('An ArcGIS patch required to run MDCS is not yet installed. Unable to proceed.', self.const_critical_text)
            return (False, self.const_init_ret_patch)
        # ends
        self.setUserDefinedValues()  # replace user defined dynamic variables in config file with values provided at the command-line.
        if (self.m_workspace == ''):
            self.m_workspace = self.prefixFolderPath(self.getAbsPath(self.getXMLNodeValue(self.m_doc, "WorkspacePath")), self.const_workspace_path_)
        if (self.m_geodatabase == ''):
            self.m_geodatabase = self.getXMLNodeValue(self.m_doc, "Geodatabase")
        if (self.m_mdName == ''):
            self.m_mdName = self.getXMLXPathValue("Application/Workspace/MosaicDataset/Name", "Name")
        const_len_ext = len(self.const_geodatabase_ext)
        ext = self.m_geodatabase[-const_len_ext:].upper()
        if (ext != self.const_geodatabase_ext and
                ext != self.const_geodatabase_SDE_ext):
            self.m_geodatabase += self.const_geodatabase_ext.lower()  # if no extension specified, defaults to '.gdb'
        self.m_gdbName = self.m_geodatabase[:len(self.m_geodatabase) - const_len_ext]  # .gdb
        self.m_geoPath = os.path.join(self.m_workspace, self.m_geodatabase)
        self.m_commands = self.getXMLNodeValue(self.m_doc, "Command")
        if (ext == self.const_geodatabase_SDE_ext):
            self.m_IsSDE = True
            try:
                self.log('Reading SDE connection properties from (%s)' % (self.m_geoPath))
                conProperties = arcpy.Describe(self.m_geoPath).connectionProperties
                self.m_SDE_database_user = ('%s.%s.') % (conProperties.database, conProperties.user)
            except Exception as inst:
                self.log(str(inst), self.const_critical_text)
                return (False, self.const_init_ret_sde)
        self.m_data['workspace'] = self.m_geoPath
        self.m_data['mosaicdataset'] = self.m_mdName
        self.m_data['sourcePath'] = self.m_sources
        return (True, 'OK')

    def invokeDynamicFnCallback(self, args, fn_name=None):
        if (fn_name is None):
            return args
        fn = fn_name.lower()
        if (self.invoke_cli_callback(fn_name, args)):
            return args
        return None

    # cli callback ptrs
    def invoke_cli_callback(self, fname, args):
        if (self.m_cli_callback_ptr is not None):
            return self.m_cli_callback_ptr(fname, args)
        return args

    def invoke_cli_msg_callback(self, mtype, args):
        if (self.m_cli_msg_callback_ptr is not None):
            return self.m_cli_msg_callback_ptr(mtype, args)
        return args
    # ends

    def setCodeBase(self, path):
        if (os.path.exists(path) == False):
            return None

        self.m_code_base = path

        self.const_statistics_path_ = os.path.join(self.m_code_base, '../../Parameter/Statistics')
        self.const_raster_function_templates_path_ = os.path.join(self.m_code_base, '../../Parameter/RasterFunctionTemplates')
        self.const_raster_type_path_ = os.path.join(self.m_code_base, '../../Parameter/RasterType')
        self.const_workspace_path_ = os.path.join(self.m_code_base, '../../')  # .gdb output
        self.const_import_geometry_features_path_ = os.path.join(self.m_code_base, '../../Parameter')

        return self.m_code_base

    def setXMLNodeValue(self, xPath, key, value, subKey, subValue):
        nodes = self.m_doc.getElementsByTagName(key)
        for node in nodes:
            parents = []
            c = node
            while(c.parentNode is not None):
                parents.insert(0, c.nodeName)
                c = c.parentNode
            p = '/'.join(parents)
            if (p == xPath):
                if (subKey != ''):
                    try:
                        if (node.firstChild.nodeValue == value):  # taking a short-cut to edit/this could change in future to support any child-node lookup
                            if (node.nextSibling.nextSibling.nodeName == subKey):
                                node.nextSibling.nextSibling.firstChild.data = subValue
                            break
                    except BaseException:
                        break
                    continue
                node.firstChild.data = value
                break

    def getXMLXPathValue(self, xPath, key):

        nodes = self.m_doc.getElementsByTagName(key)
        for node in nodes:
            parents = []
            c = node
            while(c.parentNode is not None):
                parents.insert(0, c.nodeName)
                c = c.parentNode
            p = '/'.join(parents)
            if (p == xPath):
                if (node.hasChildNodes() == False):
                    return ''
                return str(node.firstChild.data).strip()

        return ''

    def setLog(self, log):
        self.m_log = log
        return True

    def isLog(self):
        return (self.m_log is not None)

    def log(self, msg, level=const_general_text):
        if (self.m_log is not None):
            return self.m_log.Message(msg, level)

        errorTypeText = 'msg'
        if (level > self.const_general_text):
            errorTypeText = 'warning'
        elif(level == self.const_critical_text):
            errorTypeText = 'critical'

        print('log-' + errorTypeText + ': ' + msg)

        return True

    # user defined functions implementation code

    def isUser_Function(self, name):
        try:
            if (self.m_userClassInstance is None):
                return None
            fnc = getattr(self.m_userClassInstance, name)
        except BaseException:
            return False
        return True

    def invoke_user_function(self, name, data):
        ret = False
        type_event = self._is_builtin_event(name)
        try:
            if (self.m_userClassInstance is None):
                return False
            fnc = getattr(self.m_userClassInstance, name)
            try:
                ret = fnc(data)
            except Exception as inf:
                self.log(f"Executing {'event' if type_event else 'user defined function'} ({name})", self.const_critical_text)
                self.log(str(inf), self.const_critical_text)
                return False
        except Exception as inf:
            self.log(f"Please check if {'event' if type_event else 'user'} function ({name}) is found in class ({self.CCLASS_NAME}) of MDCS_UC module.", self.const_critical_text)
            self.log(str(inf), self.const_critical_text)
            return False
        return ret
    # ends

    def processEnv(self, node, pos, json):  # support fnc for 'SE' command.

        while(node.nextSibling is not None):
            if(node.nodeType != Base.NODE_TYPE_TEXT):

                k = str(pos)
                if ((k in json.keys()) == False):
                    json[k] = {'key': [], 'val': [], 'type': []}

                json[k]['key'].append(node.nodeName)
                v = ''
                if (node.firstChild is not None):
                    v = node.firstChild.nodeValue.strip()
                json[k]['val'].append(v)
                json[k]['parent'] = node.parentNode.nodeName
                json[k]['type'].append('c')

                if (node.firstChild is not None):
                    if (node.firstChild.nextSibling is not None):
                        pos = len(json)
                        json[k]['type'][len(json[k]['type']) - 1] = 'p'
                        self.processEnv(node.firstChild.nextSibling, pos, json)
                        pos = 0     # defaults to root always, assuming only 1 level deep xml.
            node = node.nextSibling

        return True

    def getAbsPath(self, input):
        absPath = input
        if (os.path.exists(absPath)):
            absPath = os.path.abspath(input)

        return absPath

    def prefixFolderPath(self, input, prefix):

        _file = input.strip()
        _p, _f = os.path.split(_file)
        _indx = _p.lower().find('.gdb')
        if (_p == '' or _indx >= 0):
            if (_indx >= 0):
                _f = _p + '\\' + _f
            _file = os.path.join(prefix, _f)

        return _file

    def isArcGISPatched(self):      # return values [true | false]

        # if we're running on python 3+, it's assumed we're on (ArcGIS Pro) and there's no need to check for patches.
        if (sys.version_info[0] >= 3):
            return True

        # if the patch XML node is not properly formatted in structure/with values, MDCS returns an error and will abort the operation.

        patch_node = self.getXMLNode(self.m_doc, "Patch")
        if (patch_node == ''):
            return True

        if (patch_node.attributes.length == 0):
            return False

        if ((self.CVERSION_ATTRIB in patch_node.attributes.keys()) == False):
            return False
        target_ver = patch_node.attributes.getNamedItem(self.CVERSION_ATTRIB).nodeValue.strip()
        if (len(target_ver) == 0):
            return False

        search_key = ''
        patch_desc_node = patch_node.firstChild.nextSibling
        while (patch_desc_node is not None):
            node_name = patch_desc_node.nodeName
            if (node_name == 'Name'):
                if (patch_desc_node.hasChildNodes()):
                    search_key = patch_desc_node.firstChild.nodeValue
                    break
            patch_desc_node = patch_desc_node.nextSibling.nextSibling

        if (len(search_key) == 0):      # if no patch description could be found, return False
            return False

        ver = (target_ver + '.0.0.0.0').split('.')
        for n in range(self.CMAJOR, self.CBUILD + 1):
            if (ver[n] == ''):
                ver[n] = 0
            ver[n] = int(ver[n])
        ver = ver[:4]       # accept only the first 4 digits.

        target_v_str = installed_v_str = ''
        for i in range(self.CMAJOR, self.CBUILD + 1):
            target_v_str += "%04d" % ver[i]

        installed_ver = self.getDesktopVersion()
        for i in range(self.CMAJOR, self.CBUILD + 1):
            installed_v_str += "%04d" % installed_ver[i]

        tVersion = int(target_v_str)
        iVersion = int(installed_v_str)

        if (iVersion > tVersion):           # the first priority is to check for the patch version against the installed version
            return True                     # if the installed ArcGIS version is greater than the patch's, it's OK to proceed.
        if (self.isLinux()):
            return True
        # if the installed ArcGIS version is lower than the intended target patch version, continue with the registry key check for the
        # possible patches installed.
        # HKEY_LOCAL_MACHINE\SOFTWARE\Wow6432Node\ESRI\Desktop10.2\Updates

        CPRODUCT_NAME = 'ProductName'
        CVERSION = 'Version'

        setupInfo = arcpy.GetInstallInfo()
        if ((CVERSION in setupInfo.keys()) == False or
                (CPRODUCT_NAME in setupInfo.keys()) == False):
            return False

        key = setupInfo[CPRODUCT_NAME] + setupInfo[CVERSION]

        try:
            reg_path = "Software\\Wow6432Node\\ESRI\\%s\\Updates" % (key)
            arcgis = OpenKey(
                HKEY_LOCAL_MACHINE, reg_path)

            i = 0
            while True:
                name = EnumKey(arcgis, i)
                arcgis_sub = OpenKey(
                    HKEY_LOCAL_MACHINE, reg_path + '\\' + name)
                try:
                    value, type = QueryValueEx(arcgis_sub, "Name")
                    if (type == 1):   # reg_sz
                        if (value.lower().find(search_key.lower()) >= 0):
                            return True     # return true if the value is found!
                except Exception as exp:
                    log.Message(str(exp), log.const_warning_text)
                    pass
                i += 1
        except Exception as exp:
            log.Message(str(exp), log.const_warning_text)
            pass

        return False

    def getDesktopVersion(self):  # returns major, minor, sp and the build number.

        d = arcpy.GetInstallInfo()

        version = []

        buildNumber = 0
        spNumber = 0

        CVERSION = 'version'
        CBUILDNUMBER = 'buildnumber'
        CSPNUMBER = 'spnumber'

        ValError = False

        for k in d:
            key = k.lower()
            if (key == CVERSION or
                key == CBUILDNUMBER or
                    key == CSPNUMBER):
                try:
                    if (key == CVERSION):
                        [version.append(int(x)) for x in d[k].split(".")]
                    elif (key == CBUILDNUMBER):
                        buildNumber = int(d[k])
                    elif (key == CSPNUMBER):
                        spNumber = int(d[k])        # could be N/A
                except BaseException:
                    ValError = True

        CMAJOR_MINOR_REVISION = 3
        if (len(version) < CMAJOR_MINOR_REVISION):  # On a system with full-install, ArcGIS version piece of information could return 3 numbers (major, minor, revision/SP)
            version.append(spNumber)                # and thus the SP number shouldn't be added to the version sperately.
        version.append(buildNumber)

        return version

    def CheckMDCSVersion(self, min, max, print_err_msg=True):
        if (not sum(min) and
            not sum(max)):
            self.log('Config version check is disabled.', self.const_warning_text)
            return True     # ver check disabled
        CMAJOR = 0
        CMINOR = 1
        CSP = 2
        CBUILD = 3
        min_major = min[CMAJOR]
        min_minor = min[CMINOR]
        min_sp = min[CSP]
        min_build = min[CBUILD]
        max_major = max[CMAJOR]
        max_minor = max[CMINOR]
        max_cp = max[CSP]
        max_build = max[CBUILD]
        min_ver = (min.pop(0) << 16 | min.pop(0) << 8 | min.pop(0)) << 32 | min.pop(0)
        max_ver = (max.pop(0) << 16 | max.pop(0) << 8 | max.pop(0)) << 32 | max.pop(0)
        try:
            version = self.getDesktopVersion()
            if len(version) >= self.const_ver_len:  # major, minor, sp, build
                inst_major = version[CMAJOR]
                inst_minor = version[CMINOR]
                inst_sp = version[CSP]
                inst_build = version[CBUILD]
                inst_version = (version.pop(0) << 16 | version.pop(0) << 8 | version.pop(0)) << 32 | version.pop(0)
                ver_failed = False
                if max_ver:
                    if inst_version > max_ver:
                        ver_failed = True
                if min_ver:
                    if inst_version < min_ver:
                        ver_failed = True
                if ver_failed:
                    if print_err_msg:
                        self.log("MDCS can't proceed due to ArcGIS version incompatiblity.", self.const_critical_text)
                        self.log(
                            f"ArcGIS Desktop version is ({inst_major}.{inst_minor}.{inst_sp}.{inst_build}). MDCS min and max versions are ({min_major}.{min_minor}.{min_sp}.{min_build}) and ({max_major}.{max_minor}.{max_cp}.{max_build}) respectively.",
                            self.const_critical_text,
                        )
                    return False
        except Exception as inst:
            self.log(f"Version check failed: ({inst})", self.const_critical_text)
            return False
        return True

    def getXMLNodeValue(self, doc, nodeName):
        if (doc is None):
            return ''
        node = doc.getElementsByTagName(nodeName)

        if (node is None or
            node.length == 0 or
            node[0].hasChildNodes() == False or
                node[0].firstChild.nodeType != Base.NODE_TYPE_TEXT):
            return ''

        return node[0].firstChild.data

    def updateART(self, doc, workspace, dataset):
        if (doc is None):
            return False
        if (workspace.strip() == ''
                and dataset.strip() == ''):
            return False        # nothing to do.
        try:
            nodeName = 'Key'
            node_list = doc.getElementsByTagName(nodeName)
            for node in node_list:
                if (node.hasChildNodes()):
                    _nValue = node.firstChild.nodeValue
                    if (_nValue):
                        _nValue = _nValue.lower()
                        if (_nValue == 'dem' or
                                _nValue == 'database'):
                            _node = node.nextSibling
                            while(_node):
                                if (_node.hasChildNodes() and
                                        _node.firstChild.nodeValue):
                                    _node.firstChild.nodeValue = '{}'.format(
                                        os.path.join(workspace, dataset) if _nValue == 'dem' else workspace)
                                    break
                                _node = _node.nextSibling
            nodeName = 'NameString'
            node_list = doc.getElementsByTagName(nodeName)
            for node in node_list:
                if (node.hasChildNodes()):
                    vals = node.firstChild.nodeValue.split(';')
                    upd_buff = []
                    for v in vals:
                        vs = v.split('=')
                        for vs_ in vs:
                            vs_ = vs_.lower()
                            if (vs_.find('workspace') > 0):
                                if (workspace != ''):
                                    vs[1] = ' ' + workspace
                                    _node = node.nextSibling
                                    while(_node):
                                        if (_node.nodeName == 'PathName'):
                                            _node.firstChild.nodeValue = workspace
                                            break
                                        _node = _node.nextSibling
                            elif (vs_.find('rasterdataset') > 0):
                                if (dataset != ''):
                                    vs[1] = ' ' + dataset
                                    _node = node.previousSibling
                                    while(_node):
                                        if (_node.nodeName == 'Name'):
                                            _node.firstChild.nodeValue = dataset
                                            break
                                        _node = _node.previousSibling
                        upd_buff.append('='.join(vs))
                    if (len(upd_buff) > 0):
                        upd_nodeValue = ';'.join(upd_buff)
                        node.firstChild.nodeValue = upd_nodeValue
        except Exception as inst:
            self.log(str(inst), self.const_critical_text)
            return False
        return True

    def getInternalPropValue(self, dic, key):
        if (key in dic.keys()):
            return dic[key]
        else:
            return ''

    def setUserDefinedValues(self):

        nodes = self.m_doc.getElementsByTagName('*')
        for node in nodes:
            if node.firstChild is not None:
                v = node.firstChild.data.strip()
                if v.find('$') == -1:
                    continue
                usr_key = v
                default = ''
                d = self.get_split_values(v, ';')
                if len(d) > 1:
                    default = d[0].strip()
                    usr_key = d[1].strip()
                revalue = []
                first = usr_key.find('$')
                first += 1
                second = first + usr_key[first + 1:].find('$') + 1
                if first > 1:
                    revalue.append(usr_key[0:first - 1])
                while second >= 0:
                    uValue = usr_key[first:second]
                    if uValue.upper() in self.m_dynamic_params.keys():
                        revalue.append(self.m_dynamic_params[uValue.upper()])
                    else:
                        if uValue.find(r'\$') >= 0:
                            uValue = uValue.replace(r'\$', '$')
                        else:
                            if default == '':
                                default = uValue
                            if (first == 1
                                    and second == (len(usr_key) - 1)):
                                uValue = default
                        revalue.append(uValue)
                    first = second + 1
                    indx = usr_key[first + 1:].find('$')
                    if indx == -1:
                        if first != len(usr_key):
                            revalue.append(usr_key[first:len(usr_key)])
                        break
                    second = first + indx + 1
                updateVal = ''.join(revalue)
                node.firstChild.data = updateVal

    def getXMLNode(self, doc, nodeName):
        if (doc is None):
            return ''
        node = doc.getElementsByTagName(nodeName)

        if (node is None or
            node.length == 0 or
            node[0].hasChildNodes() == False or
                node[0].firstChild.nodeType != Base.NODE_TYPE_TEXT):
            return ''

        return node[0]

    def foundLockFiles(self, folder_path):

        file_list_ = os.listdir(folder_path)
        found_lock_ = False
        for i in file_list_:
            if (i[-5:].lower() == '.lock'):
                sp = i.split('.')
                pid = os.getpid()
                if (pid == int(sp[3])):  # indx 3 == process id
                    found_lock_ = True
                    break

        return found_lock_

    def waitForLockRelease(self, folder_path_):

        if (os.path.exists(folder_path_) == False):
            self.log('lock file path does not exist!. Quitting...', self.const_critical_text)
            return -2  # path does not exist error code!

        t0 = datetime.now()
        duration_req_sec_ = 3
        max_time_to_wait_sec_ = 10
        tot_count_sec_ = 0

        while True:
            if (tot_count_sec_ == 0):
                if (self.foundLockFiles(folder_path_) == False):  # try to see if we could get lucky on the first try, else enter periodic check.
                    break
            t1 = datetime.now() - t0

            if (t1.seconds > duration_req_sec_):
                if (self.foundLockFiles(folder_path_) == False):
                    break
                tot_count_sec_ += duration_req_sec_
                if (tot_count_sec_ > max_time_to_wait_sec_):
                    self.log('lock file release timed out!. Quitting...', self.const_critical_text)
                    tot_count_sec_ = -1
                    break
                t0 = datetime.now()

        return tot_count_sec_

    @staticmethod
    def isLinux(self):
        return sys.platform.lower().startswith(('linux', 'darwin'))

    def getBooleanValue(self, value):
        if (value is None):
            return False
        if (isinstance(value, bool)):
            return value
        val = value
        if (not isinstance(val, str)):
            val = str(val)
        val = val.lower()
        if val in ['true', 'yes', 't', '1', 'y']:
            return True
        return False

    def _updateResponse(self, resp, **kwargs):
        if (resp is None):
            return resp
        for k in kwargs:
            resp[k] = kwargs[k]
        return resp

    def _getResponseResult(self, resp):
        if (resp is None):
            return False
        if (isinstance(resp, bool)):
            status = resp
        elif (isinstance(resp, dict)):
            status = False
            if ('status' in resp):
                status = self.getBooleanValue(resp['status'])
        return status

    def get_split_values(self, in_str, sep):
        '''
            Split the input string around {sep} while escaping \{sep}
        '''
        values = []
        escape_marker = -2
        if (not in_str or
            len(in_str.strip()) == 0):
            return values
        start = 0
        while start <= len(in_str):
            end = escape_marker
            upd_st = start
            while end == escape_marker:
                end = in_str.find(sep, upd_st)
                if end == -1:
                    end = len(in_str)
                    break
                if in_str[end - 1] == '\\':
                    upd_st = end + 1
                    end = escape_marker
                    continue
            values.append(in_str[start:end].replace(f'\\{sep}', sep))
            start = end + 1
        return values

    def _is_builtin_event(self, fnc_name: str):
        if fnc_name is None:
            return False
        return fnc_name in [self.EVT_ON_EXIT, self.EVT_ON_START]
