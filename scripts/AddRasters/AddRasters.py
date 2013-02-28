#-------------------------------------------------------------------------------
# Name  	    	: AddRasters.py
# ArcGIS Version	: ArcGIS 10.1 sp1
# Script Version	: 20130225
# Name of Company 	: Environmental System Research Institute
# Author        	: ESRI raster solution team
# Date          	: 16-09-2012
# Purpose 	    	: A component to Add rasters/data to existing mosaic datasets.
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
class AddRasters(Base.Base):

    geodatabase_ext = '.gdb'

    gdbName = ''
    gdbNameExt = ''
    doc = None
    sMdNameList = {}
    geoPath = ''
    workspace = ''
    callback_functions = []
    m_MD = ''
    m_sources = ''
    m_base = None


    def __init__(self, base=None):
        if (base != None):
            self.setLog(base.m_log)
            self.workspace = base.m_workspace
            self.gdbNameExt = base.m_geodatabase
            self.m_MD = base.m_md
            self.m_sources = base.m_sources

        self.m_base = base

    def AddCallBack(self, fnc):
        self.callback_functions.append(fnc)
        return True



    def AddRasters(self):

        self.log("Adding rasters:", self.const_general_text)
        ml =0
        for sourceID in self.sMdNameList:

            MDName = self.sMdNameList[sourceID]['md']

            for hshAddRaster in self.sMdNameList[sourceID]['addraster']:
                try:
                    self.log("\tUsing mosaic dataset/ID:" + MDName + '/' + \
                    hshAddRaster['dataset_id'], self.const_general_text)

                    fullPath = self.geoPath + '/' + MDName
                    if arcpy.Exists(fullPath):

                        rasterType = 'Raster Dataset'

                        name_toupper = MDName.upper()
                        if (hshAddRaster.has_key('art')):
                            rasterType = hshAddRaster['art']
                            self.log("\tUsing ART for " + name_toupper + ': ' + rasterType, self.const_general_text)

                        set_filter = ''

                        if (hshAddRaster.has_key('filter')):
                            set_filter = hshAddRaster['filter']
                            if (set_filter == '*'):
                                set_filter = ''
                        set_spatial_reference = ''
                        if (hshAddRaster.has_key('spatial_reference')):
                            set_spatial_reference = hshAddRaster['spatial_reference']

                        try:
                            t_view = "table_view" + str(ml)
                            ml = ml+1
                            arcpy.MakeTableView_management(fullPath,t_view)
                            rows = arcpy.SearchCursor(t_view,"","","OBJECTID")
                            obvalue = 0
                            if rows != None :
                                for row in rows:
                                    obvalue =  row.ObjectID

                            self.sMdNameList[sourceID]['pre_AddRasters_record_count'] = obvalue
                            self.sMdNameList[sourceID]['Dataset_ID'] = hshAddRaster['dataset_id']
                        except:
                            self.log('Failed to make Table View Layer', self.const_warning_text)
                            self.log(arcpy.GetMessages(), self.const_warning_text)
                        try:
                            arcpy.Delete_management(t_view)
                        except:
                            self.log("failed to Delete the layer " + t_view, self.const_warning_text)
                            self.log(arcpy.GetMessages(), self.const_warning_text)

                        try:
                            arcpy.AddRastersToMosaicDataset_management(fullPath, rasterType, hshAddRaster['data_path'],'NO_CELL_SIZES','NO_BOUNDARY','','','','',set_spatial_reference, set_filter)
                        except:
                            self.log("Failed to add rasters to mosaic dataset : " + fullPath, self.const_warning_text)
                            self.log(arcpy.GetMessages(), self.const_warning_text)

                        for callback_fn in self.callback_functions:
                            callback_fn(self.geoPath, sourceID, self.sMdNameList[sourceID])

                    else:
                        self.log("Error: Path doesn't exist:" + fullPath, self.const_warning_text)
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


        #workspace/location on filesystem where the .gdb is created.
        if (self.workspace == ''):
            self.workspace = self.prefixFolderPath(self.getXMLNodeValue(self.doc, "WorkspacePath"), self.const_workspace_path_)
        if (self.gdbNameExt == ''):
            self.gdbNameExt =  self.getXMLNodeValue(self.doc, "Geodatabase")
        const_len_ext = 4
        if (self.gdbNameExt[-const_len_ext:].lower() != self.geodatabase_ext):
            self.gdbNameExt += '.gdb'


        sources_ = self.m_sources.split(',')
        sources_max_ = len(sources_)
        sources_indx_ = 0


        self.gdbName = self.gdbNameExt[:len(self.gdbNameExt) - const_len_ext]       #.gdb

        self.geoPath = os.path.join(self.workspace, self.gdbNameExt)

        mdType = self.getXMLNodeValue(self.doc, 'MosaicDatasetType').lower()
        isDerived = mdType == 'derived'

        Nodelist = self.doc.getElementsByTagName("MosaicDataset")
        if (Nodelist.length == 0):
            self.log("Error: <MosaicDataset> node is not found! Invalid schema.", self.const_critical_text)
            return False

        try:
            for node in Nodelist[0].childNodes:
                  node =  node.nextSibling
                  if (node != None and node.nodeType == minidom.Node.ELEMENT_NODE):

                                if (node.nodeName == 'Name'):
                                        mosasicDataset = self.m_MD
                                        if (mosasicDataset == ''):
                                            mosasicDataset = node.firstChild.nodeValue
                                        mosasicDataset = mosasicDataset.strip()

                                        self.sMdNameList[mosasicDataset] = {'md' : mosasicDataset}
                                        self.sMdNameList[mosasicDataset]['addraster'] = []

                                        self.sMdNameList[mosasicDataset]['type'] = self.getXMLNodeValue(self.doc, "MosaicDatasetType")

                                elif(node.nodeName == 'dataset_id'):
                                    if (self.sMdNameList.has_key(mosasicDataset)):
                                        idValue = node.firstChild.nodeValue
                                        self.sMdNameList[mosasicDataset]['Dataset_ID'] = idValue.strip()

                                elif(node.nodeName == 'AddRasters'):

                                    rasterType = False

                                    if (len(mosasicDataset) == 0):
                                        self.log("Error: <Name> should be the first child-element in <MosaicDataset>", self.const_critical_text)
                                        return False

                                    for node in node.childNodes:
                                        if (node != None and node.nodeType == minidom.Node.ELEMENT_NODE):
                                            nodeName = node.nodeName.lower()

                                            if (nodeName == 'addraster'):

                                                if (sources_indx_ > 0):
                                                    break;

                                                hshAddRasters = {}

                                                for node in node.childNodes:
                                                    if (node != None and node.nodeType == minidom.Node.ELEMENT_NODE):
                                                        nodeName = node.nodeName.lower()

                                                        nodeValue = ''
#                                                        spatial_reference = ''
                                                        if (node.childNodes.length > 0):
                                                            nodeValue = node.firstChild.nodeValue

                                                        if (nodeName == 'sources'):

                                                            dataPaths =  ''
                                                            keyFound = False
                                                            nodeName = 'data_path'       #only <DataPath> nodes can exist under <Sources>

                                                            if (self.m_sources == ''):
                                                                for cNode in node.childNodes:
                                                                    if (cNode != None and cNode.nodeType == minidom.Node.ELEMENT_NODE):
                                                                        name_ = cNode.nodeName
                                                                        name_ = name_.lower()

                                                                        if (name_ == nodeName):
                                                                            if (cNode.childNodes.length > 0):
                                                                                _file  = cNode.firstChild.nodeValue.strip()
                                                                                if (isDerived):
                                                                                    _p, _f = os.path.split(_file)
                                                                                    if (_p == ''):
                                                                                        _flist = _f.split(';')
                                                                                        indata = ''
                                                                                        for _fl in range(len(_flist)):
                                                                                            indata =  indata + ";" + (os.path.join(self.geoPath,_flist[_fl]))
                                                                                        if indata[0] == ';':
                                                                                            _file = indata[1:len(indata)]
                                                                                        else:
                                                                                            _file = indata
#                                                                                        _file = os.path.join(self.geoPath, _f)

                                                                                dataPaths = dataPaths + _file + ';'
                                                                                keyFound = True

                                                            else:
                                                                if (sources_indx_ < sources_max_):
                                                                    dataPaths = sources_[sources_indx_]
                                                                    sources_indx_ += 1
                                                                    keyFound = True

                                                            if (keyFound == False):
                                                                continue

                                                            nodeValue = dataPaths


                                                        elif (nodeName == 'raster_type'):
                                                            nodeName = 'art'
                                                            if (nodeValue.lower().find('art.xml') >= 0):
                                                                nodeValue = self.prefixFolderPath(nodeValue, self.const_raster_type_path_)

                                                        elif (nodeName == 'spatial_reference'):
#                                                            nodeValue = spatial_reference
                                                            dd= 'f'

                                                        hshAddRasters[nodeName] = nodeValue

                                                if (self.sMdNameList.has_key(mosasicDataset)):
                                                    try:
                                                        self.sMdNameList[mosasicDataset]['addraster'].append(hshAddRasters)
                                                    except:
                                                        Warning_ = True
                                                        #print "Warning: empty value for: MosaicDataset/" + nodeName

        except:
            self.log("Error: reading MosaicDataset nodes.", self.const_critical_text)
            return False


        if not arcpy.Exists(self.workspace):
                self.log("Error: workspace not found!:" + self.workspace, self.const_critical_text)
                self.log(arcpy.GetMessages(), self.const_critical_text)
                return False


        return True
