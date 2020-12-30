#------------------------------------------------------------------------------
# Copyright 2013 Esri
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
#------------------------------------------------------------------------------
# Name: SetMDProperties.py
# Description: To set mosaic dataset properties
# Version: 20201230
# Requirements: ArcGIS 10.1 SP1
# Author: Esri Imagery Workflows team
#------------------------------------------------------------------------------
#!/usr/bin/env python

import os
from xml.dom import minidom
import Base
import arcpy
import numpy as np
import json
from datetime import datetime
from datetime import timedelta
solutionLib = os.path.dirname(os.path.realpath(__file__))
mdcsPath = os.path.normpath(solutionLib + os.sep + os.pardir)
paramPath = os.path.join(os.path.dirname(mdcsPath),'Parameter')
jsonPath = os.path.join(paramPath,'Json')


class SetMDProperties(Base.Base):

    def __init__(self, base):
        self.dic_properties_lst = {}
        self.dicMDs = {}

        self.setLog(base.m_log)
        self.m_base = base

    def is101SP1(self):
        return self.CheckMDCSVersion([10, 1, 0, 0], [0, 0, 0, 0])       # ver [major, minor, revision, build]

    def getInternalPropValue(self, md, key):
        if (key in self.dic_properties_lst.keys()):
            return self.dic_properties_lst[key]
        else:
            return ''

    def _message(self, msg, type):
        self.log(msg, type)

    def __setpropertiesCallback(self, args, fn_name):
        CONST_ORDER_FIELD_POS = 16
        if (self.is101SP1() == False):  # OrderField set to 'BEST' would fail in 10.1 without SP1
            args[CONST_ORDER_FIELD_POS] = 'MinPS'
        return args


    # write json from dictionary object
    def writeJson(self,filename,jsonData):
        log = self.m_base.m_log
        try:
            with open(filename, "w") as fp:
                json.dump(jsonData,fp) #dump the dictionary to the json file
            return True

        except Exception as exp:
            log.Message(str(exp),log.const_critical_text)
            return False


   # read json file and create dictionary object
    def readJson(self,jsonData):
        log = self.m_base.m_log
        try:
            jsData = json.load(open(jsonData)) #read json file and load it to dictionary object
            return jsData

        except Exception as exp:
            log.Message(str(exp),log.const_critical_text)
            return False

    # Compare two dictionary and dump the difference in dictionary to json file
    def compare_dict(self, first_dict, second_dict, outputJson):
        log = self.m_base.m_log
        # Compared two dictionaries..
        # Posts things that are not equal..
        res_compare = []
        mDifferences = {}
        try:
            log.Message("Differences",log.const_general_text)
            mDifferences["Attribute"]="First Property | Second Property"

            #getting the comman keys in between two dictionaries
            common_keys = first_dict.keys() & second_dict.keys()
            for k in set(common_keys):
                if isinstance(first_dict[k], dict):
                    z0 = self.compare_dict(first_dict[k], second_dict[k])
                else:
                    z0 = first_dict[k] == second_dict[k]

                z0_bool = np.all(z0)
                res_compare.append(z0_bool)
                if not z0_bool:
                    mDifferences[k]= str(first_dict[k])+ " | "+str(second_dict[k])
                    message = "Property:"+str(k)+" --->>> First Mosaic:"+str(first_dict[k])+ "  |||  Second Mosaic:"+str(second_dict[k])
                    log.Message(message,log.const_general_text)

            self.writeJson(outputJson,mDifferences)
            log.Message("Completed",log.const_general_text)
            return np.all(res_compare)

        except Exception as exp:
            log.Message(str(exp),log.const_critical_text)
            return False


    #Extracting the property of mosaic and dumping properties to dictionar file
    def mosaicProperty(self,mdObj):
        log = self.m_base.m_log
        # dictionary to match the name between MDCS config nodes and arcpy descripe mosaic properties
        propertyDict = {
            "rows_maximum_imagesize":"maxRequestSizeY",
            "columns_maximum_imagesize":"maxRequestSizeX",
            "allowed_compressions":"allowedCompressionMethods",
            "default_compression_type":"defaultCompressionMethod",
            "JPEG_quality":"JPEGQuality",
            "LERC_Tolerance":"LERCTolerance",
            "resampling_type":"defaultResamplingMethod",
            "clip_to_footprints":"clipToFootprint",
            "footprints_may_contain_nodata":"footprintMayContainNoData",
            "clip_to_boundary":"clipToBoundary",
            "color_correction":"applyColorCorrection",
            "allowed_mensuration_capabilities":"allowedMensurationCapabilities",
            "default_mensuration_capabilities":"defaultMensurationCapability",
            "allowed_mosaic_methods":"allowedMosaicMethods",
            "default_mosaic_method":"defaultMosaicMethod",
            "order_field":"orderField",
            "order_base":"orderBaseValue",
            "sorting_order":"sortAscending",
            "mosaic_operator":"mosaicOperator",
            "blend_width":"blendWidth",
            "view_point_x":"viewpointSpacingX",
            "view_point_y":"viewpointSpacingY",
            "max_num_per_mosaic":"maxRastersPerMosaic",
            "cell_size_tolerance":"cellSizeToleranceFactor",
            "metadata_level":"rasterMetadataLevel",
            "use_time":"useTime",
            "start_time_field":"startTimeField",
            "end_time_field":"endTimeField",
            "time_format":"timeValueFormat",
            "geographic_transform":"GCSTransforms",
            "max_num_of_download_items":"maxDownloadImageCount",
            "max_num_of_records_returned":"maxRecordsReturned",
            "minimum_pixel_contribution":"minimumPixelContribution",
            "processing_templates":"processingTemplates",
            "default_processing_template":"defaultProcessingTemplate"
        }
        dictObj = {}
        try:
            MosaicObj = arcpy.Describe(mdObj)
            for key,value in propertyDict.items():
                if key == "resampling_type":
                    dictObj[key] = getattr(MosaicObj, value).split(' ', 1 )[0].upper()
                elif key == "processing_templates":
                    dictObj[key]="None"
                else:
                    dictObj[key] = getattr(MosaicObj, value)

            return dictObj

        except Exception as exp:
            log.Message(str(exp),log.const_critical_text)
            return False

    #set property of the Mosaic using json
    def setPropertybyJson(self,inputJson):
        log = self.m_base.m_log
        try:
            jsData = self.readJson(inputJson)
            try:
                if len(jsData)>0:
                    for attribute in jsData:
                        self.dic_properties_lst[attribute] = jsData[attribute] #assign the each property of mosaic with dictionary
            except Exception as exp:
                log.Message(str(exp),self.const_critical_text)
                return False
            return True
        except Exception as exp:
            log.Message(str(exp),self.const_critical_text)
            return False


    #extract property of the Mosaic and dump to json
    def extractPropertytoJson(self,mdObj,outputJson):
        log = self.m_base.m_log
        try:
            dictObj = self.mosaicProperty(mdObj) #read mosaic property
            self.writeJson(outputJson,dictObj)
            return True

        except Exception as exp:
            log.Message(str(exp),self.self.const_critical_text)
            return False



    #set property of the Mosaic by reference mosaic
    def setPropertyByMosaic(self,external_mosaic):
        log = self.m_base.m_log
        try:
            if arcpy.Exists(external_mosaic):
                jsData = self.mosaicProperty(external_mosaic)
                try:
                    if len(jsData)>0:
                        for attribute in jsData:

                            self.dic_properties_lst[attribute] = jsData[attribute] #assign the each property of mosaic with dictionary

                except Exception as exp:
                    log.Message(str(exp),log.const_critical_text)
                    return False
            else:
                log.Message("Given input is not found or invalid",self.const_critical_text)
            return True

        except Exception as exp:
            log.Message(str(exp),self.const_critical_text)
            return False


    #compare properties of two mosiac
    def comparePropertyByMosiac(self,internal_mosaic,external_mosaic,outputJson):
        log = self.m_base.m_log
        try:
            if arcpy.Exists(internal_mosaic):
                firstMosaicProperty = self.mosaicProperty(internal_mosaic)
            else:
                log.Message("Given Mosaic is not found or invalid",self.const_critical_text)

            if arcpy.Exists(external_mosaic):
                secondMosiacProperty = self.mosaicProperty(external_mosaic)
            else:
                log.Message("Given Mosaic is not found or invalid",self.const_critical_text)

            self.compare_dict(firstMosaicProperty,secondMosiacProperty,outputJson)
            return True

        except Exception as exp:
            log.Message(str(exp),self.const_critical_text)
            return False

    #compare properties of a mosaic and json (userinput)
    def comparePropertyByJson(self,internal_mosaic,inputJson,outputJson):
        log = self.m_base.m_log
        try:
            if arcpy.Exists(internal_mosaic):
                firstMosaicProperty = self.mosaicProperty(internal_mosaic)
            else:
                log.Message("Given Mosaic is not found or invalid",self.const_critical_text)


            secondMosiacProperty = self.readJson(inputJson)

            self.compare_dict(firstMosaicProperty,secondMosiacProperty,outputJson)
            return True

        except Exception as exp:
            log.Message(str(exp),self.const_critical_text)
            return False


    #set property of the mosaic
    def setProperty(self, mdPath):
        args = []
        mdName = os.path.basename(mdPath).upper()
        args.append(mdPath)
        args.append(self.getInternalPropValue(mdName, 'rows_maximum_imagesize'))
        args.append(self.getInternalPropValue(mdName, 'columns_maximum_imagesize'))
        args.append(self.getInternalPropValue(mdName, 'allowed_compressions'))
        args.append(self.getInternalPropValue(mdName, 'default_compression_type'))
        args.append(self.getInternalPropValue(mdName, 'JPEG_quality'))
        args.append(self.getInternalPropValue(mdName, 'LERC_Tolerance'))
        args.append(self.getInternalPropValue(mdName, 'resampling_type'))
        args.append(self.getInternalPropValue(mdName, 'clip_to_footprints'))
        args.append(self.getInternalPropValue(mdName, 'footprints_may_contain_nodata'))
        args.append(self.getInternalPropValue(mdName, 'clip_to_boundary'))
        args.append(self.getInternalPropValue(mdName, 'color_correction'))
        args.append(self.getInternalPropValue(mdName, 'allowed_mensuration_capabilities'))
        args.append(self.getInternalPropValue(mdName, 'default_mensuration_capabilities'))
        args.append(self.getInternalPropValue(mdName, 'allowed_mosaic_methods'))
        args.append(self.getInternalPropValue(mdName, 'default_mosaic_method'))
        args.append(self.getInternalPropValue(mdName, 'order_field'))
        args.append(self.getInternalPropValue(mdName, 'order_base'))
        args.append(self.getInternalPropValue(mdName, 'sorting_order'))
        args.append(self.getInternalPropValue(mdName, 'mosaic_operator'))
        args.append(self.getInternalPropValue(mdName, 'blend_width'))
        args.append(self.getInternalPropValue(mdName, 'view_point_x'))
        args.append(self.getInternalPropValue(mdName, 'view_point_y'))
        args.append(self.getInternalPropValue(mdName, 'max_num_per_mosaic'))
        args.append(self.getInternalPropValue(mdName, 'cell_size_tolerance'))
        args.append(self.getInternalPropValue(mdName, 'cell_size'))
        args.append(self.getInternalPropValue(mdName, 'metadata_level'))
        args.append(self.getInternalPropValue(mdName, 'transmission_fields'))
        args.append(self.getInternalPropValue(mdName, 'use_time'))
        args.append(self.getInternalPropValue(mdName, 'start_time_field'))
        args.append(self.getInternalPropValue(mdName, 'end_time_field'))
        args.append(self.getInternalPropValue(mdName, 'time_format'))
        args.append(self.getInternalPropValue(mdName, 'geographic_transform'))
        args.append(self.getInternalPropValue(mdName, 'max_num_of_download_items'))
        args.append(self.getInternalPropValue(mdName, 'max_num_of_records_returned'))
        args.append(self.getInternalPropValue(mdName, 'data_source_type'))
        args.append(self.getInternalPropValue(mdName, 'minimum_pixel_contribution'))
        args.append(self.getInternalPropValue(mdName, 'processing_templates'))
        args.append(self.getInternalPropValue(mdName, 'default_processing_template'))
        args.append(self.getInternalPropValue(mdName, 'time_interval'))
        args.append(self.getInternalPropValue(mdName, 'time_interval_units'))
        setProperties = Base.DynaInvoke('arcpy.SetMosaicDatasetProperties_management', args, self.__setpropertiesCallback, self._message)

        if (setProperties.init() == False):
            return False
        return setProperties.invoke()

    #set property of the mosaic based on the user defined flag
    def setMDProperties(self, mdPath):
        base = self.m_base
        xmlDOM = self.m_base.m_doc
        log = self.m_base.m_log

        sp_inputjson = base.getXMLNodeValue(xmlDOM, 'sp_inputjson')
        sp_mosaic = base.getXMLNodeValue(xmlDOM, 'sp_mosaic')
        sp_outputjson = base.getXMLNodeValue(xmlDOM, 'sp_outputjson')
        sp_flag = base.getXMLNodeValue(xmlDOM, 'sp_flag')


        try:
            if sp_flag == "setpropertybyjson":
                if sp_inputjson == "#":
                    log.Message("Error: Missing Json file to Set property",self.const_critical_text)
                    return False
                else:
                    absPathCheck = os.path.isabs(sp_inputjson)
                    if absPathCheck == False:
                        sp_inputjson = os.path.join(jsonPath,sp_inputjson)
                    self.setPropertybyJson(sp_inputjson)
                    self.setProperty(mdPath)

            elif sp_flag == "setpropertybymosiac":
                if sp_mosaic == "#":
                    log.Message("Error: MosaicDataset not found!",self.const_critical_text)
                    return False
                else:
                    self.setPropertyByMosaic(sp_mosaic)
                    self.setProperty(mdPath)


            elif sp_flag == "extractproperty":
                if sp_outputjson == "#":
                    log.Message("Missing Ouput file to Extract property",self.const_critical_text)
                    log.Message("Extracting property to Parameter/Json/",self.const_critical_text)
                    sp_outputjson = os.path.join(jsonPath,"mosaicProperty"+str(datetime.strftime(datetime.now(),"%Y%m%d%H%M%S"))+".json")
                    self.extractPropertytoJson(mdPath,sp_outputjson)
                else:
                    self.extractPropertytoJson(mdPath,sp_outputjson)


            elif sp_flag == "compareproperty":
                if sp_mosaic == "#":
                    if sp_inputjson == "#":
                        log.Message("Error: MosaicDataset / Input Json not found!",self.const_critical_text)
                    else:
                        if sp_outputjson == "#":
                            log.Message("Missing Ouput file to Extract property",self.const_critical_text)
                            log.Message("Extracting property to Parameter/Json/",self.const_critical_text)
                            sp_outputjson = os.path.join(jsonPath,"compare"+str(datetime.strftime(datetime.now(),"%Y%m%d%H%M%S"))+".json")
                            absPathCheck = os.path.isabs(sp_inputjson)
                            if absPathCheck == False:
                                sp_inputjson = os.path.join(jsonPath,sp_inputjson)
                        self.comparePropertyByJson(mdPath,sp_inputjson,sp_outputjson)


                else:
                    if sp_outputjson == "#":
                        log.Message("Missing Ouput file to Extract property",self.const_critical_text)
                        log.Message("Extracting property to Parameter/Json/compare.json",self.const_critical_text)
                        sp_outputjson = os.path.join(jsonPath,"compare"+str(datetime.strftime(datetime.now(),"%Y%m%d%H%M%S"))+".json")
                    self.comparePropertyByMosiac(mdPath,sp_mosaic,sp_outputjson)

            else:
                log.Message("SP flag is not found!",self.const_critical_text)
                log.Message("Using default for Set property",self.const_critical_text)
                self.setProperty(mdPath)

            return True

        except Exception as exp:
            log.Message(str(exp),self.const_critical_text)
            return False



    def init(self, config):

        Nodelist = self.m_base.m_doc.getElementsByTagName("MosaicDataset")
        if (Nodelist.length == 0):
            self.log("Error: MosaicDataset node not found! Invalid schema.", self.const_critical_text)
            return False

        try:
            for node in Nodelist[0].childNodes:
                node = node.nextSibling
                if (node is not None and node.nodeType == minidom.Node.ELEMENT_NODE):
                    if (node.nodeName == 'DefaultProperties'):
                        for node in node.childNodes:
                            ptvalue = node.firstChild.nodeValue if node.firstChild else ''
                            if (node.nodeType == minidom.Node.ELEMENT_NODE):
                                if (node.nodeName == 'processing_templates' or
                                        node.nodeName == 'default_processing_template'):
                                    if (ptvalue != '#' and
                                            ptvalue != ''):
                                        ptvaluesplit = ptvalue.split(';')
                                        rftpaths = ''
                                        for each in ptvaluesplit:
                                            if (each.find('/') == -1):
                                                if (each.lower() == 'none'):        # 'none' is an acceptable value.
                                                    rftpaths = rftpaths + each
                                                else:
                                                    rftpaths = rftpaths + os.path.abspath(os.path.join((self.m_base.const_raster_function_templates_path_), each))
                                                rftpaths += ';'
                                        ptvalue = rftpaths = rftpaths[:-1]
                                self.dic_properties_lst[node.nodeName] = ptvalue
        except:
            Error = True

        return True
