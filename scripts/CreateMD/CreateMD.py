#-------------------------------------------------------------------------------
# Name  	    	: CreateMD.py
# ArcGIS Version	: ArcGIS 10.1 sp1
# Script Version	: 20130225
# Name of Company 	: Environmental System Research Institute
# Author        	: ESRI raster solution team
# Date          	: 16-09-2012
# Purpose 	    	: A component to create source mosaic datasets.
# Created	    	: 14-08-2012
# LastUpdated  		: 17-09-2012
# Required Argument 	: Not applicable
# Optional Argument 	: Not applicable
# Usage         	: Object of this class should be instantiated.
# Copyright	    	: (c) ESRI 2012
# License	    	: <your license>
#-------------------------------------------------------------------------------

import arcpy,os,sys
from xml.dom import minidom

import Base

class CreateMD(Base.Base):

    geodatabase_ext = '.gdb'
    srs = ''
    pixel_type = ''
    doc = None
    workspace = ''
    gdbName = ''
    gdbNameExt = ''
    m_base = None
    product_definition = ''
    num_bands = ''
    product_band_definitions = ''
    m_MD = ''

    def __init__(self, base=None):
        if (base != None):
            self.setLog(base.m_log)
            self.workspace = base.m_workspace
            self.gdbNameExt = base.m_geodatabase
            self.m_MD = base.m_md

        self.m_base = base


    def createGeodataBase(self):

        # create output workspace if missing.
        if (os.path.exists(self.workspace) == False):
            try:
                os.makedirs(self.workspace)
            except:
                self.log("Failed to create folder: " + self.workspace, self.const_critical_text)
                self.log(arcpy.GetMessages(), self.const_critical_text)
                return False

        # create Geodatabase
        try:
            if self.gdbName[(len(self.gdbName)-4):len(self.gdbName)] != '.gdb':
                gdbPath = os.path.join(self.workspace, self.gdbName) + self.geodatabase_ext
            else:
                gdbPath = os.path.join(self.workspace, self.gdbName)
            self.log("Creating Geodatabase: "+ gdbPath, self.const_general_text)
            if not os.path.exists(gdbPath):
                arcpy.CreateFileGDB_management(self.workspace, self.gdbName)
            else:
                self.log("\tFile geodatabase already exists!", self.const_warning_text)
            return True
        except:
            return False



    def createMD(self):

        gdbPath = os.path.join(self.workspace, self.gdbNameExt)
        self.log("Creating source mosaic datasets:", self.const_general_text)

        try:
            mdPath = os.path.join(gdbPath, self.m_MD)
            if not arcpy.Exists(mdPath):
                self.log("\t" + self.m_MD, self.const_general_text)
                arcpy.CreateMosaicDataset_management(gdbPath,self.m_MD,self.srs,self.num_bands,self.pixel_type,self.product_definition,self.product_band_definitions)

        except:
            self.log("Failed!", self.const_critical_text)
            self.log(arcpy.GetMessages(), self.const_critical_text)
            return False

        return True


    def init(self, config):

        try:
            self.doc = minidom.parse(config)
        except:
            self.log("Error: reading input config file:" + config + "\nQuitting...", self.const_critical_text)
            return False


        # Step (1)                      #get path to .gdb
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
            self.log("\nError: MosaicDatasets node not found! Invalid schema.", self.const_critical_text)
            return False

        try:
            for node in Nodelist[0].childNodes:
                  node =  node.nextSibling
                  if (node != None and node.nodeType == minidom.Node.ELEMENT_NODE):
                      if (node.nodeName == 'Name'):
                            try:
                                if (self.m_MD == ''):
                                    self.m_MD = node.firstChild.nodeValue
                            except:
                                Error = True
                      elif(node.nodeName == 'SRS'):
                            self.srs = node.firstChild.nodeValue
                      elif(node.nodeName == 'pixel_type'):
                            self.pixel_type = node.firstChild.nodeValue
                      elif(node.nodeName == 'num_bands'):
                            self.num_bands = node.firstChild.nodeValue
                      elif(node.nodeName == 'product_definition'):
                            self.product_definition = node.firstChild.nodeValue
                      elif(node.nodeName == 'product_band_definitions'):
                            self.product_band_definitions = node.firstChild.nodeValue
        except:
            self.log("\nError: reading MosaicDataset nodes.", self.const_critical_text)
            return False

        return True


