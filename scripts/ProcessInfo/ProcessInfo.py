#-------------------------------------------------------------------------------
# Name  	    	: ProcessInfo.py
# ArcGIS Version	: ArcGIS 10.1 sp1
# Script Version	: 20131205
# Name of Company 	: Environmental System Research Institute
# Author        	: ESRI raster solution team
# Purpose 	    	: Class to Read in process info values from config XML files.
# Created	    	: 14-08-2012
# LastUpdated  		: 11-06-2013
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

    processInfo = {}
    userProcessInfo = {}

    def __init__(self, base=None):

        self.m_base = base
        self.setLog(base.m_log)
        self.processInfo = {}
        self.userProcessInfo = {}

        self.hasProcessInfo = False
        self.userProcessInfoValues  = False


    def getXML(self):
        if (self.m_base.m_doc != None
        and self.config != ''):
            return self.m_base.m_doc.toxml()


    def updateProcessInfo(self, pInfo):
            self.userProcessInfoValues = True
            self.userProcessInfo = pInfo
            return self.init(self.config)

    def init(self, config):

        self.config = config
        self.processInfo = {}
        self.hasProcessInfo = False

        Nodelist = self.m_base.m_doc.getElementsByTagName("MosaicDataset")
        if (Nodelist.length == 0):
            self.log ("Error: <MosaicDataset> node is not found! Invalid schema.",
            self.const_critical_text)
            return False

        try:
            for node in Nodelist[0].childNodes:
                  node =  node.nextSibling
                  if (node != None and node.nodeType == minidom.Node.ELEMENT_NODE):

                                if(node.nodeName == 'Processes'):

                                    for node in node.childNodes:
                                        if (node != None and
                                            node.nodeType == minidom.Node.ELEMENT_NODE):

                                            procesName = node.nodeName
                                            procesName = procesName.lower()

                                            if (self.m_hsh_parent_child_nodes.has_key(procesName)):
                                                parentNode  = self.m_hsh_parent_child_nodes[procesName]['parent']
                                                childNode = self.m_hsh_parent_child_nodes[procesName]['child']

                                                if (self.processInfo.has_key(parentNode) == False):
                                                    self.processInfo[parentNode] = []

                                                aryCV = []

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
                                                            aryCV.append (hashCV)
                                                self.processInfo[parentNode].append(aryCV)
                                                continue


                                            if (self.processInfo.has_key(procesName) == False):
                                                self.processInfo[procesName] = []

                                            hashCV = {}
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
                                                                node.appendChild(self.m_base.m_doc.createTextNode(value))
                                                            node.firstChild.nodeValue = value

                                                        value = node.firstChild.nodeValue
                                                    except:
                                                        Warning_ = True

                                                    hashCV[key] = value
                                            self.processInfo[procesName].append(hashCV)

        except Exception as inst:
            self.log ("Error: Reading <MosaicDataset> node.",
            self.const_critical_text)
            return False

        if (len (self.processInfo) > 0):
            self.hasProcessInfo = True

        self.userProcessInfoValues = False

        return True


