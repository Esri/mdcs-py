#-------------------------------------------------------------------------------
# Name  	    	: ProcessInfo.py
# ArcGIS Version	: ArcGIS 10.1 sp1
# Script Version	: 20130225
# Name of Company 	: Environmental System Research Institute
# Author        	: ESRI raster solution team
# Date          	: 16-09-2012
# Purpose 	    	: Class to Read in process info values from config XML files.
# Created	    	: 14-08-2012
# LastUpdated  		: 13-05-2013
# Required Argument 	: Not applicable
# Optional Argument 	: Not applicable
# Usage         	:  Object of this class should be instantiated.
# Copyright	    	: (c) ESRI 2012
# License	    	: <your license>
#-------------------------------------------------------------------------------
#!/usr/bin/env python
from xml.dom import minidom
import os
import Base

class ProcessInfo(Base.Base):


    m_hsh_parent_child_nodes = \
    {
        'addindex' :
            {   'parent' : 'addindex',
                'child' : 'index'
            },
        'calculatevalues' :
            {   'parent' : 'calculatevalues',
                'child' : 'calculatevalue'
            }
    }

    hasProcessInfo = False
    userProcessInfoValues  = False
    const_geodatabase_ext = '.GDB'

    doc = None
    processInfo = {}
    userProcessInfo = {}

    gdbName = ''
    gdbNameExt = ''
    geoPath = ''
    workspace = ''
    mdName = ''
    config = ''
    commands = ''

    m_base = None

    def __init__(self, base=None):

        self.gdbName = ''
        self.gdbNameExt = ''
        self.geoPath = ''
        self.workspace = ''
        self.mdName = ''
        self.config = ''
        self.commands = ''

        self.m_base = None

        if (base != None):
            self.setLog(base.m_log)
            self.workspace = base.m_workspace
            self.gdbNameExt = base.m_geodatabase
            self.mdName = base.m_md
            self.processInfo = {}
            self.userProcessInfo = {}

            self.doc = None
            self.hasProcessInfo = False
            self.userProcessInfoValues  = False

        self.m_base = base

    def getXML(self):
        if (self.doc != None
        and self.config != ''):
            return self.doc.toxml()


    def updateProcessInfo(self, pInfo):
            self.userProcessInfoValues = True
            self.userProcessInfo = pInfo
            return self.init(self.config)

    def init(self, config):

        try:
            self.doc = minidom.parse(config)
        except:
            self.log("Error: reading input config file:" + config + "\nQuitting...",
            self.const_critical_text)
            return False

        self.config = config
        self.processInfo = {}
        self.hasProcessInfo = False

        #workspace/location on filesystem where the .gdb is created.
        if (self.workspace == ''):
            self.workspace = self.prefixFolderPath(self.m_base.getAbsPath(self.getXMLNodeValue(self.doc, "WorkspacePath")), self.const_workspace_path_)

        if (self.gdbNameExt == ''):
            self.gdbNameExt =  self.getXMLNodeValue(self.doc, "Geodatabase")

        const_len_ext = len(self.const_geodatabase_ext)
        if (self.gdbNameExt[-const_len_ext:].upper() != self.const_geodatabase_ext):
            self.gdbNameExt += self.const_geodatabase_ext.lower()


        self.gdbName = self.gdbNameExt[:len(self.gdbNameExt) - const_len_ext]       #.gdb
        self.geoPath = os.path.join(self.workspace, self.gdbNameExt)

        self.commands = self.getXMLNodeValue(self.doc, "Command")

        Nodelist = self.doc.getElementsByTagName("MosaicDataset")
        if (Nodelist.length == 0):
            self.log ("Error: <MosaicDataset> node is not found! Invalid schema.",
            self.const_critical_text)
            return False

        try:
            for node in Nodelist[0].childNodes:
                  node =  node.nextSibling
                  if (node != None and node.nodeType == minidom.Node.ELEMENT_NODE):

                                if (node.nodeName == 'Name'):
                                    if (self.mdName == ''):
                                        self.mdName = node.firstChild.nodeValue.strip()

                                elif(node.nodeName == 'Processes'):

                                    for node in node.childNodes:
                                        if (node != None and
                                            node.nodeType == minidom.Node.ELEMENT_NODE):

                                            procesName = node.nodeName
                                            procesName = procesName.lower()

                                            if (self.processInfo.has_key(procesName) == False):

                                                if (self.m_hsh_parent_child_nodes.has_key(procesName)):
                                                    parentNode  = self.m_hsh_parent_child_nodes[procesName]['parent']
                                                    childNode = self.m_hsh_parent_child_nodes[procesName]['child']

                                                    self.processInfo[parentNode] = []
                                                    for node in node.childNodes:
                                                        if (node != None and node.nodeType == minidom.Node.ELEMENT_NODE):

                                                            key = node.nodeName.lower()
                                                            if (key == childNode):
                                                                hashCV = {}
                                                                for node in node.childNodes:
                                                                    if (node != None and node.nodeType == minidom.Node.ELEMENT_NODE):
                                                                        keyName = node.nodeName.lower()
                                                                        value = '#'     #set GP tool default value for argument.
                                                                        try:
                                                                            value = node.firstChild.nodeValue
                                                                        except:
                                                                            Warning_ = True
                                                                        hashCV[keyName] = value
                                                                self.processInfo[parentNode].append(hashCV)

                                                    continue

                                                self.processInfo[procesName] = {}

                                            for node in node.childNodes:
                                                if (node != None and node.nodeType == minidom.Node.ELEMENT_NODE):

                                                    key = node.nodeName
                                                    key = key.lower()

                                                    value = '#'     #set GP tool default value for argument.
                                                    try:
                                                        if (self.userProcessInfoValues):
                                                            value = self.userProcessInfo[procesName][key]
                                                            if (value == '#'):
                                                                value = ''
                                                            if (node.childNodes.length == 0):
                                                                node.appendChild(self.doc.createTextNode(value))
                                                            node.firstChild.nodeValue = value

                                                        value = node.firstChild.nodeValue
                                                    except:
                                                        Warning_ = True

                                                    self.processInfo[procesName][key] = value

        except:
            self.log ("Error: Reading <MosaicDataset> node.",
            self.const_critical_text)
            return False

        if (len (self.processInfo) > 0):
            self.hasProcessInfo = True

        self.userProcessInfoValues = False

        return True


