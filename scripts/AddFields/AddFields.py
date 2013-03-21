#-------------------------------------------------------------------------------
# Name  	    	: AddFields.py
# ArcGIS Version	: ArcGIS 10.1 sp1
# Script Version	: 20130225
# Name of Company 	: Environmental System Research Institute
# Author        	: ESRI raster solution team
# Date          	: 16-09-2012
# Purpose 	    	: A component to create custom fields in mosaic datasets.
# Created	    	: 14-08-2012
# LastUpdated  		: 17-09-2012
# Required Argument 	: Not applicable.
# Optional Argument 	: Not applicable.
# Usage         	: Object of this class should be instantiated.
# Copyright	    	: (c) ESRI 2012
# License	    	: <your license>
#-------------------------------------------------------------------------------

import arcpy,os,sys
from xml.dom import minidom

import Base

class AddFields(Base.Base):
    geodatabase_ext = '.gdb'

    gdbName = ''
    gdbNameExt = ''
    doc = None
    workspace = ''
    gdbPath =  ''
    m_MD = ''
    fieldNameList = []
    fieldTypeList = []
    fieldLengthList = []
    m_base = None

    def __init__(self, base=None):
        if (base != None):
            self.setLog(base.m_log)
            self.workspace = base.m_workspace
            self.gdbNameExt = base.m_geodatabase
            self.m_MD = base.m_md

        self.m_base = base


    def CreateFields(self):

        self.log("Adding custom fields:", self.const_general_text)

        self.log("Using mosaic dataset:" + self.m_MD, self.const_general_text)
        try:
            mdPath = os.path.join(self.gdbPath, self.m_MD)
            if not arcpy.Exists(mdPath):
                self.log("Mosaic dataset is not found.", self.const_warning_text)
                return False

            self.log("\tCreating fields:", self.const_general_text)
            for j in range(len(self.fieldNameList)):
                self.log("\t\t" + self.fieldNameList[j], self.const_general_text)
                fieldExist = arcpy.ListFields(mdPath,self.fieldNameList[j])
                if len(fieldExist) == 0:
                    arcpy.AddField_management(mdPath,self.fieldNameList[j],self.fieldTypeList[j],"","",self.fieldLengthList[j])
##                    workspace = self.m_base.m_workspace
##                    geodatabase = self.m_base.m_geodatabase
##                    if (workspace == ''):
##                        workspace = self.workspace
##                    if (geodatabase == ''):
##                        geodatabase = self.gdbName
##                    lock_path_  = os.path.join(workspace, geodatabase + '.gdb')
##                    result_code_  = self.waitForLockRelease(lock_path_)
##                    if (result_code_ == -1):
##                        return False
##                    elif(result_code_ == -2):
##                        return False

        except:
            self.log("Error: " + arcpy.GetMessages(), self.const_critical_text)
            return False

        return True



    def init(self, config):

        try:
            self.doc = minidom.parse(config)
        except:
            self.log("Error: reading input config file:" + sys.argv[1] + "\nQuitting...", self.const_critical_text)
            return False


        # Step (1)
        #workspace/location on filesystem where the .gdb is created.
        if (self.workspace == ''):
            self.workspace = self.prefixFolderPath(self.getXMLNodeValue(self.doc, "WorkspacePath"), self.const_workspace_path_)

        if (self.gdbNameExt == ''):
            self.gdbNameExt =  self.getXMLNodeValue(self.doc, "Geodatabase")

        const_len_ext = 4
        if (self.gdbNameExt[-const_len_ext:].lower() != self.geodatabase_ext):
            self.gdbNameExt += '.gdb'


        self.gdbName = self.gdbNameExt[:len(self.gdbNameExt) - const_len_ext]       #.gdb


        Nodelist = self.doc.getElementsByTagName("MosaicDataset")
        if (Nodelist.length == 0):
            self.log("\nError: MosaicDataset node not found! Invalid schema.", self.const_critical_text)
            return False

        try:
            for node in Nodelist[0].childNodes:
                  node =  node.nextSibling
                  if (node != None and node.nodeType == minidom.Node.ELEMENT_NODE):
                    if (node.nodeName == 'Name'):
                        try:
                            if (self.m_MD == ''):
                                self.m_MD = node.firstChild.nodeValue
                            break
                        except:
                            Error = True
        except:
            self.log("\nError: reading MosaicDataset nodes.", self.const_critical_text)
            return False


        Nodelist = self.doc.getElementsByTagName("Fields")
        if (Nodelist.length == 0):
            self.log("Error: Fields node not found! Invalid schema.", self.const_critical_text)
            return False


        try:
            for node in Nodelist[0].childNodes:
              if (node.nodeType == minidom.Node.ELEMENT_NODE):
                for n in node.childNodes:
                    if(n.nodeType == minidom.Node.ELEMENT_NODE):
                        nodeName = n.nodeName.upper()
                        if (nodeName == 'NAME'):
                            self.fieldNameList.append(n.firstChild.nodeValue)
                        elif(nodeName == 'TYPE'):
                            self.fieldTypeList.append(n.firstChild.nodeValue)
                        elif(nodeName == 'LENGTH'):
                            try:
                                self.fieldLengthList.append(n.firstChild.nodeValue)
                            except:
                                self.fieldLengthList.append('')
        except:
            self.log("\nError: Reading fields information!", self.const_critical_text)
            return False


        fields_len = len(self.fieldNameList)
        if (len(self.fieldTypeList) != fields_len or len(self.fieldLengthList) != fields_len):
            self.log("\nError: Number of Field(Name, Type, Len) do not match!", self.const_critical_text)
            return False


        self.gdbPath = os.path.join(self.workspace, self.gdbNameExt)

        return True

