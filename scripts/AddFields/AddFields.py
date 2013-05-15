#-------------------------------------------------------------------------------
# Name  	    	: AddFields.py
# ArcGIS Version	: ArcGIS 10.1 sp1
# Script Version	: 20130225
# Name of Company 	: Environmental System Research Institute
# Author        	: ESRI raster solution team
# Date          	: 16-09-2012
# Purpose 	    	: A component to create custom fields in mosaic datasets.
# Created	    	: 14-08-2012
# LastUpdated  		: 13-05-2013
# Required Argument 	: Not applicable
# Optional Argument 	: Not applicable
# Usage         	: Object of this class should be instantiated.
# Copyright	    	: (c) ESRI 2012
# License	    	: <your license>
#-------------------------------------------------------------------------------

import arcpy,os,sys
from xml.dom import minidom

import Base

class AddFields(Base.Base):

    fieldNameList = []
    fieldTypeList = []
    fieldLengthList = []

    def __init__(self, base):
        self.setLog(base.m_log)
        self.m_base = base


    def CreateFields(self):

        self.log("Adding custom fields:", self.const_general_text)

        self.log("Using mosaic dataset:" + self.m_base.m_mdName, self.const_general_text)
        try:
            mdPath = os.path.join(self.m_base.m_geoPath, self.m_base.m_mdName)
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

        Nodelist = self.m_base.m_doc.getElementsByTagName("MosaicDataset")
        if (Nodelist.length == 0):
            self.log("\nError: MosaicDataset node not found! Invalid schema.", self.const_critical_text)
            return False

        try:
            for node in Nodelist[0].childNodes:
                  node =  node.nextSibling
                  if (node != None and node.nodeType == minidom.Node.ELEMENT_NODE):
                    if (node.nodeName == 'Name'):
                        try:
                            if (self.m_base.m_mdName == ''):
                                self.m_base.m_mdName = node.firstChild.nodeValue
                            break
                        except:
                            Error = True
        except:
            self.log("\nError: reading MosaicDataset nodes.", self.const_critical_text)
            return False


        Nodelist = self.m_base.m_doc.getElementsByTagName("Fields")
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

        return True

