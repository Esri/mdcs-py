#-------------------------------------------------------------------------------
# Name  	    	: Base.py
# ArcGIS Version	: ArcGIS 10.1 sp1
# Script Version	: 20130528
# Name of Company 	: Environmental System Research Institute
# Author        	: ESRI raster solution team
# Purpose 	    	: Base call used by all Raster Solutions components.
# Created	    	: 14-08-2012
# LastUpdated  		: 28-05-2013
# Required Argument 	: Not applicable
# Optional Argument 	: Not applicable
# Usage         	:  Object of this class should be instantiated.
# Copyright	    	: (c) ESRI 2012
# License	    	: <your license>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

import os
from datetime import datetime

from xml.dom import minidom
scriptPath = os.path.dirname(__file__)

class Base(object):

#begin - constansts
    const_general_text = 0
    const_warning_text = 1
    const_critical_text = 2
    const_status_text = 3

    const_statistics_path_ = os.path.join(scriptPath, '..\\..\\parameter\\Statistics')
    const_raster_function_templates_path_ = os.path.join(scriptPath, '..\\..\\parameter\\RasterFunctionTemplates')
    const_raster_type_path_ = os.path.join(scriptPath, '..\\..\\parameter\\Rastertype')
    const_workspace_path_ = os.path.join(scriptPath, '..\\..\\')      #.gdb output
    const_import_geometry_features_path_ = os.path.join(scriptPath, '..\\..\\parameter')

    const_cmd_default_text = "#defaults"
    const_geodatabase_ext = '.GDB'

#ends

    def __init__(self):
        self.m_log = None
        self.m_doc = None

#the follwoing variables could be overridden by the command-line to replace respective values in XML config file.
        self.m_workspace = ''
        self.m_geodatabase = ''
        self.m_mdName = ''  #mosaic dataset name.
#ends

        self.m_sources = ''

        self.m_gdbName = ''
        self.m_geoPath = ''
        self.m_config = ''
        self.m_commands = ''

        self.m_sources = ''  #source data paths for adding new rasters.

        self.m_dynamic_params = {}

    def init(self):

        if (self.m_doc == None):
            return False

        self.setUserDefinedValues()         #replace user defined dynamic variables in config file with values provided at the command-line.

        if (self.m_workspace == ''):
            self.m_workspace = self.prefixFolderPath(self.getAbsPath(self.getXMLNodeValue(self.m_doc, "WorkspacePath")), self.const_workspace_path_)

        if (self.m_geodatabase == ''):
            self.m_geodatabase =  self.getXMLNodeValue(self.m_doc, "Geodatabase")

        if (self.m_mdName == ''):
            self.m_mdName =  self.getXMLXPathValue("Application/Workspace/MosaicDataset/Name", "Name")


        const_len_ext = len(self.const_geodatabase_ext)
        if (self.m_geodatabase[-const_len_ext:].upper() != self.const_geodatabase_ext):
            self.m_geodatabase += self.const_geodatabase_ext.lower()


        self.m_gdbName = self.m_geodatabase[:len(self.m_geodatabase) - const_len_ext]       #.gdb
        self.m_geoPath = os.path.join(self.m_workspace, self.m_geodatabase)

        self.m_commands = self.getXMLNodeValue(self.m_doc, "Command")

        return True


    def getXMLXPathValue(self, xPath, key):

        nodes = self.m_doc.getElementsByTagName(key)
        for node in nodes:
            parents = []
            c = node
            while(c.parentNode != None):
                parents.insert(0, c.nodeName)
                c = c.parentNode
            p = '/'.join(parents)
            if (p == xPath):
                return str(node.firstChild.data).strip()

        return ''

    def setLog(self, log):
        self.m_log = log
        return True

    def isLog(self):
        return (not self.m_log == None)

    def log(self, msg, level = const_general_text):
        if (self.m_log != None):
            return self.m_log.Message(msg, level)

        errorTypeText = 'msg'
        if (level > self.const_general_text):
             errorTypeText = 'warning'
        elif(level == self.const_critical_text):
             errorTypeText = 'critical'

        print 'log-' + errorTypeText + ': ' + msg

        return True


    def getAbsPath(self, input):
        absPath = input
        if (os.path.exists(absPath) == True):
            absPath = os.path.abspath(input)

        return absPath


    def prefixFolderPath(self, input, prefix):

        _file  = input.strip()
        _p, _f = os.path.split(_file)
        _indx = _p.lower().find('.gdb')
        if (_p == '' or _indx >= 0):
            if (_indx >= 0):
                _f   = _p + '\\' + _f
            _file = os.path.join(prefix, _f)

        return _file

    def getXMLNodeValue(self, doc, nodeName) :
        if (doc == None):
            return ''
        node = doc.getElementsByTagName(nodeName)
        if (node == None or
            node.length == 0 or
            node[0].firstChild.nodeType != minidom.Node.TEXT_NODE):
            return ''

        return node[0].firstChild.data


    def getInternalPropValue(self, dic, key):
        if (dic.has_key(key)):
            return dic[key]
        else:
            return ''


    def setUserDefinedValues(self):

        nodes = self.m_doc.getElementsByTagName('*')
        for node in nodes:
            if (node.firstChild != None):
                 v = node.firstChild.data.strip()

                 if (v.find('$') == -1):
                    continue

                 usr_key = v
                 default = ''

                 d = v.split(';')

                 if (len(d) > 1):
                    default = d[0].strip()
                    usr_key = d[1].strip()

                 revalue = []

                 first = usr_key.find('$')
                 first += 1

                 second =  first + usr_key[first+1:].find('$') + 1

                 if (first > 1):
                    revalue.append(usr_key[0:first - 1])

                 while(second >= 0):

                    while(usr_key[second - 1: second] == '\\'):
                        indx = usr_key[second+1:].find('$')
                        if (indx == -1):
                            indx = len(usr_key) - 1

                        second = second + indx + 1

                    uValue = usr_key[first:second]

                    if (self.m_dynamic_params.has_key(uValue.upper())):
                        revalue.append(self.m_dynamic_params[uValue.upper()])
                    else:
                        if (uValue.find('\$') >= 0):
                            uValue = uValue.replace('\$', '$')
                        else:
                            if (default == ''):
                                default = uValue

                            if (first == 1
                            and second == (len(usr_key) - 1)):
                                uValue = default

                        revalue.append(uValue)

                    first = second + 1
                    indx = usr_key[first+1:].find('$')
                    if (indx == -1):
                        if (first != len(usr_key)):
                            revalue.append(usr_key[first:len(usr_key)])
                        break

                    second = first + indx + 1

                 updateVal = ''.join(revalue)
                 node.firstChild.data = updateVal



    def getXMLNode(self, doc, nodeName) :
        if (doc == None):
            return ''
        node = doc.getElementsByTagName(nodeName)
        if (node == None or
            node.length == 0 or
            node[0].firstChild.nodeType != minidom.Node.TEXT_NODE):
            return ''

        return node[0]

    def foundLockFiles(self, folder_path):

        file_list_ = os.listdir(folder_path)
        found_lock_ = False
        for i in file_list_:
            if (i[-5:].lower() == '.lock'):
                sp = i.split('.')
                pid = os.getpid()
                if (pid == int(sp[3])):         #indx 3 == process id
                    found_lock_ = True
                    break;

        return found_lock_


    def waitForLockRelease(self, folder_path_):

        if (os.path.exists(folder_path_) == False):
            self.log('lock file path does not exist!. Quitting...', self.const_critical_text)
            return -2       #path does not exist error code!

        t0 = datetime.now()
        duration_req_sec_ = 3
        max_time_to_wait_sec_ = 10
        tot_count_sec_ = 0

        while True:
            if (tot_count_sec_ == 0):
                if (self.foundLockFiles(folder_path_) == False):   #try to see if we could get lucky on the first try, else enter periodic check.
                    break;
            t1 = datetime.now() - t0

            if (t1.seconds > duration_req_sec_):
                if (self.foundLockFiles(folder_path_) == False):
                    break;
                tot_count_sec_ += duration_req_sec_
                if (tot_count_sec_ > max_time_to_wait_sec_):
                    self.log('lock file release timed out!. Quitting...', self.const_critical_text)
                    tot_count_sec_ = -1
                    break;
                t0 = datetime.now()

        return tot_count_sec_


