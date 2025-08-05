# -------------------------------------------------------------------------------
# Copyright 2025 Esri
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# -------------------------------------------------------------------------------
# Name:  SolutionsLib.py
# Description:  To map MDCS command codes to GP Tool functions.
# Version: 20250611
# Requirements:  ArcGIS 10.1 SP1
# Optional Arguments: <optional args if any>
# Usage: solutionsLib.py [arguments]
# Author:  Esri Imagery Workflows Team
# -------------------------------------------------------------------------------
#!/usr/bin/env python

import sys
import os
from string import ascii_letters
from datetime import datetime, timezone
from inspect import signature, stack
import threading
import time
import logging
from defusedxml import minidom
import arcpy
import Base.Base as MBase
from Base.Base import Base as CBase
from constants import (
    RD_HOST,
    RD_PORT,
    RD_QUEUE_NAME,
    RD_CHANNEL,
    RT_WF_END,
    RT_INF,
    RT_CUR_CMD,
    RT_PMO,
    PERC_MAX,
    MSG_INF,
    MSG_WRN,
    MSG_ERR,
    UC_CMD_TYPE_EVENT,
    UC_CMD_TYPE_USER,
    UC_CMD_TYPE_UNKNOWN,
)
scriptPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(scriptPath, "Base"))
MOD_NAME = "SOLUTIONSLIB"
ACTIVE_IDLE_TIMEOUT = 300
CALLSTACK_SEP = "->"
JOB_ID = "job_id"
ISO_DT = "%Y-%m-%d %H:%M:%S"
FLDS_SEP = ","
logger = logging.getLogger()


def returnLevelDetails(tilingSchema):
    doc = minidom.parse(tilingSchema)
    lodNodesList = []
    lodNodes = doc.getElementsByTagName("LODInfo")
    for lodNode in lodNodes:
        level = lodNode.getElementsByTagName("LevelID")[0].firstChild.data
        levelDict = {
            "level": level,
            "scale": lodNode.getElementsByTagName("Scale")[0].firstChild.data,
            "resolution": lodNode.getElementsByTagName("Resolution")[0].firstChild.data,
        }
        lodNodesList.append(levelDict)
    return lodNodesList


def modifyConfProperties(properties, maxScale):
    doc = minidom.parse(properties)
    keys = doc.getElementsByTagName("Key")
    values = doc.getElementsByTagName("Value")
    key = [k for k in keys if k.childNodes[0].nodeValue == "MaxScale"][0]
    value = [v for v in values if v.parentNode.isSameNode(key.parentNode)][0]
    value.childNodes[0].replaceWholeText(maxScale)
    modifiedXML = doc.toxml()
    with open(properties, "w") as xmlHandler:
        xmlHandler.write(modifiedXML)


class LogHandler(logging.Handler):
    """callback class to override the loggging/emit"""

    def __init__(self, handler):
        super().__init__()
        self.callback = handler

    def emit(self, record):
        self.callback(record)


class Solutions(CBase):
    """Solutions class implements the builtin GPTool commands"""

    processInfo = None
    userInfo = None
    config = ""
    m_base = None

    def __init__(self, base=None):
        if base is not None:
            self.setLog(base.m_log)
        self.m_base = base
        self.processInfo = None
        self.userInfo = None
        self.config = ""
        self.log_csv_filepath = None

    def getAvailableCommands(self):
        return self.commands

    def __invokeDynamicFnCallback(self, args, fn_name=None):
        if fn_name is None:
            return args
        fn = fn_name.lower()
        if fn == "arcpy.exportmosaicdatasetitems_management":
            try:
                CONST_OUTPUT_FOLDER_INDX = 1
                # let's create the output folder before invoking the function
                # call.
                get_output_folder = args[CONST_OUTPUT_FOLDER_INDX]
                os.makedirs(get_output_folder)
            except BaseException:
                pass  # pass onto default error handler.
        elif fn == "arcpy.stageservice_server":
            try:
                CONST_OUT_SRV_INDX = 1
                if os.path.exists(args[CONST_OUT_SRV_INDX]):
                    os.remove(args[CONST_OUT_SRV_INDX])
            except BaseException:
                pass
        return args

    def __invokeDynamicFn(self, args, processKey, fn_name, index, **kwargs):
        try:
            nspce = fn_name.split(".")
            cls = nspce.pop()
            fnc_ptr = getattr(sys.modules[".".join(nspce)], cls)
            varnames = list(signature(fnc_ptr).parameters)
            varcount = len(signature(fnc_ptr).parameters)
            varnames = varnames[:varcount]
            for i in range(len(args), len(varnames)):
                args.append(self.getProcessInfoValue(processKey, varnames[i].lower(), index))
            for i in range(0, len(varnames)):
                # the default marker (#) as returned by (getProcessInfoValue)
                # gets replaced with (None)
                if args[i] == "#":
                    args[i] = None
            Info = "info"
            if args[0] is None and Info in kwargs and "md" in kwargs[Info]:
                # Use the loaded MosaicDataset as the first argument to the
                # function if first arg isn't defined/omitted in the config
                # file.
                args[0] = kwargs[Info]["md"]
            dynCall = MBase.DynaInvoke(fn_name, args, self.__invokeDynamicFnCallback, self.m_log.Message)
            respInfo = self.getProcessInfoValue(processKey, "returnvalue", index)
            kwargs = {}
            FnPntrPrefix = "("
            FnPntrSuffix = ")"
            if -1 != respInfo.find(FnPntrPrefix):
                fn, args = respInfo.split(FnPntrPrefix)
                fnArgs = args.split(",")  # scan for multi-args
                if fnArgs[-1][-1] != FnPntrSuffix:
                    self.m_log.Message("Syntax error for sub->method calls.", self.m_log.const_critical_text)
                    return False
                fnArgs[-1] = fnArgs[-1][:-1]
                for i in range(0, len(fnArgs)):
                    types = [float, int, str]
                    while types:
                        try:
                            val = types[0](fnArgs[i])
                            if isinstance(val, float):
                                # int values w/o the decimal point'll be
                                # ignored as floats.
                                if -1 == fnArgs[i].find("."):
                                    types.pop(0)
                                    continue
                            fnArgs[i] = val
                            break
                        except BaseException:
                            types.pop(0)
                kwargs["sArgs"] = [[fn, *fnArgs]]
            if dynCall.init(**kwargs) == False:
                return False
            response = dynCall.invoke()
            return response
        except Exception as exp:
            self.log(str(exp), self.m_log.const_critical_text)
            self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
            return False

    # mapping commands to functions
    def executeCommand(self, com, index=0):
        # create the geodatabse to hold all relevant mosaic datasets.
        fullPath = os.path.join(self.m_base.m_geoPath, self.m_base.m_mdName)  # MD path used in the MDCS w/f
        invokeDynamicFnInfo = {"md": fullPath}
        if com == "CM":
            from CreateMD.CreateMD import CreateMD
            createMD = CreateMD(self.m_base)
            bSuccess = createMD.init(self.config)
            if bSuccess:
                bSuccess = self.m_base._getResponseResult(createMD.createGeodataBase())
                if not bSuccess:
                    return False
                return createMD.createMD()
            return False

        # Add custom fields to elevation mosaic datasets.
        elif com == "AF":
            from AddFields.AddFields import AddFields

            addFields = AddFields(self.m_base)
            bSuccess = addFields.init(self.config)
            if bSuccess:
                return addFields.CreateFields()
            return False

        # Add rasters/data to mosaic datasets.
        elif com == "AR":
            from AddRasters.AddRasters import AddRasters

            addRasters = AddRasters(self.m_base)
            bSuccess = addRasters.init(self.config)
            if bSuccess:
                if com in self.userInfo.keys():
                    if "cb" in self.userInfo[com].keys():
                        bSuccess = addRasters.AddCallBack(self.userInfo[com]["cb"])
                return addRasters.AddRasters()
            return False
        # Create referenced mosaic datasets.
        elif com == "CR":
            from CreateRefMD.CreateRefMD import CreateReferencedMD

            createRefMD = CreateReferencedMD(self.m_base)
            bSuccess = createRefMD.init(self.config)
            if bSuccess:
                return createRefMD.createReferencedMD()
            return False
        elif com == "SP":
            from SetMDProperties.SetMDProperties import SetMDProperties

            setProps = SetMDProperties(self.m_base)
            bSuccess = setProps.init(self.config)
            if bSuccess:
                path = os.path.join(self.m_base.m_geoPath, self.m_base.m_mdName)
                return setProps.setMDProperties(path)
            return False
        elif com == "CBMD":
            try:
                self.m_log.Message("\tColor Balancing mosaic dataset : " + self.m_base.m_mdName, self.m_log.const_general_text)
                processKey = "colorbalancemosaicdataset"
                arcpy.ColorBalanceMosaicDataset_management(
                    fullPath,
                    self.getProcessInfoValue(processKey, "balancing_method", index),
                    self.getProcessInfoValue(processKey, "color_surface_type", index),
                    self.getProcessInfoValue(processKey, "target_raster", index),
                    self.getProcessInfoValue(processKey, "exclude_raster", index),
                    self.getProcessInfoValue(processKey, "stretch_type", index),
                    self.getProcessInfoValue(processKey, "gamma", index),
                    self.getProcessInfoValue(processKey, "block_field", index),
                )
                return True
            except BaseException:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False
        # Remove Index from Mosaic dataset.
        elif com == "RI":
            processKey = "removeindex"
            try:
                self.log("Removing Index(%s) " % (self.getProcessInfoValue(processKey, "index_name", index)))
                arcpy.RemoveIndex_management(fullPath, self.getProcessInfoValue(processKey, "index_name", index))
                self.log(arcpy.GetMessages())
                return True
            except BaseException:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False
        # Remove raster/Items from Mosaic dataset.
        elif com == "RRFMD":
            try:
                self.m_log.Message("\tRemove rasters from mosaic dataset : " + self.m_base.m_mdName, self.m_log.const_general_text)
                processKey = "removerastersfrommosaicdataset"
                arcpy.RemoveRastersFromMosaicDataset_management(
                    fullPath,
                    self.getProcessInfoValue(processKey, "where_clause", index),
                    self.getProcessInfoValue(processKey, "update_boundary", index),
                    self.getProcessInfoValue(processKey, "mark_overviews_items", index),
                    self.getProcessInfoValue(processKey, "delete_overview_images", index),
                    self.getProcessInfoValue(processKey, "delete_item_cache", index),
                    self.getProcessInfoValue(processKey, "remove_items", index),
                    self.getProcessInfoValue(processKey, "update_cellsize_ranges", index),
                )
                return True
            except BaseException:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False
        # Delete mosaic dataset.
        elif com == "DMD":
            try:
                self.m_log.Message("\tDelete Mosaic dataset  : " + self.m_base.m_mdName, self.m_log.const_general_text)
                processKey = "deletemosaicdataset"
                arcpy.DeleteMosaicDataset_management(
                    fullPath,
                    self.getProcessInfoValue(processKey, "delete_overview_images", index),
                    self.getProcessInfoValue(processKey, "delete_item_cache", index),
                )
                return True
            except BaseException:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False
        # Merge mosaic dataset
        elif com == "MMDI":
            try:
                self.m_log.Message("\tMerge mosaic dataset  Items: " + self.m_base.m_mdName, self.m_log.const_general_text)
                processKey = "mergemosaicdatasetitems"
                arcpy.MergeMosaicDatasetItems_management(
                    fullPath,
                    self.getProcessInfoValue(processKey, "where_clause", index),
                    self.getProcessInfoValue(processKey, "block_field", index),
                    self.getProcessInfoValue(processKey, "max_rows_per_merged_items", index),
                )
                return True
            except BaseException:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False
        elif com == "ERF":
            try:
                self.m_log.Message("\tEditing raster function : " + self.m_base.m_mdName, self.m_log.const_general_text)
                processKey = "editrasterfunction"
                rfunction_path = self.getProcessInfoValue(processKey, "function_chain_definition", index)
                if rfunction_path.find(".rft") > -1 and rfunction_path.find("/") == -1:
                    rfunction_path = self.m_base.const_raster_function_templates_path_ + "/" + rfunction_path
                lyrName = "lyr_%s" % str(self.m_base.m_last_AT_ObjectID)
                expression = "OBJECTID >%s" % (str(self.m_base.m_last_AT_ObjectID))
                arcpy.MakeMosaicLayer_management(fullPath, lyrName, expression)

                arcpy.EditRasterFunction_management(
                    lyrName,
                    self.getProcessInfoValue(processKey, "edit_mosaic_dataset_item", index),
                    self.getProcessInfoValue(processKey, "edit_options", index),
                    rfunction_path,
                    self.getProcessInfoValue(processKey, "location_function_name", index),
                )
                arcpy.Delete_management(lyrName)
                return True
            except BaseException:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False
        elif com == "ANCP":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            return self.__invokeDynamicFn([fullPath], "analyzecontrolpoints", "arcpy.AnalyzeControlPoints_management", index)
        elif com == "APCP":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            return self.__invokeDynamicFn([], "appendcontrolpoints", "arcpy.AppendControlPoints_management ", index)
        elif com == "ABA":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            return self.__invokeDynamicFn([fullPath], "applyblockadjustment", "arcpy.ApplyBlockAdjustment_management", index)
        elif com == "CBA":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            return self.__invokeDynamicFn([fullPath], "computeblockadjustment", "arcpy.ComputeBlockAdjustment_management", index)
        elif com == "CCP":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            return self.__invokeDynamicFn([fullPath], "computecontrolpoints", "arcpy.ComputeControlPoints_management", index)
        elif com == "CTP":
            self.m_log.Message("\tCompute Tie Points : " + self.m_base.m_mdName, self.m_log.const_general_text)
            return self.__invokeDynamicFn([fullPath], "computetiepoints", "arcpy.ComputeTiePoints_management", index)
        elif com == "AMDS":
            self.m_log.Message("\tAlter Mosaic Dataset Schema : " + self.m_base.m_mdName, self.m_log.const_general_text)
            return self.__invokeDynamicFn([fullPath], "altermosaicdatasetschema", "arcpy.AlterMosaicDatasetSchema_management", index)
        elif com == "AMD":
            self.m_log.Message(r"\Analyze Mosaic Dataset : " + self.m_base.m_mdName, self.m_log.const_general_text)
            return self.__invokeDynamicFn([fullPath], "analyzemosaicdataset", "arcpy.AnalyzeMosaicDataset_management", index)
        elif com == "BMDIC":
            self.m_log.Message(r"\Build Mosaic Dataset Item Cache : " + self.m_base.m_mdName, self.m_log.const_general_text)
            return self.__invokeDynamicFn([fullPath], "buildmosaicdatasetitemcache", "arcpy.BuildMosaicDatasetItemCache_management", index)
        elif com == "CDA":
            self.m_log.Message(r"\Compute Dirty Area : " + self.m_base.m_mdName, self.m_log.const_general_text)
            return self.__invokeDynamicFn([fullPath], "computedirtyarea", "arcpy.ComputeDirtyArea_management", index)
        elif com == "GEA":
            self.m_log.Message(r"\Generate Exclude Area : " + self.m_base.m_mdName, self.m_log.const_general_text)
            return self.__invokeDynamicFn([], "generateexcludearea", "arcpy.GenerateExcludeArea_management", index)
        elif com == "CS":
            try:
                self.m_log.Message("\tCalculate statistic for the mosaic dataset : " + self.m_base.m_mdName, self.m_log.const_general_text)
                processKey = "calculatestatistics"
                arcpy.CalculateStatistics_management(
                    fullPath,
                    self.getProcessInfoValue(processKey, "x_skip_factor", index),
                    self.getProcessInfoValue(processKey, "y_skip_factor", index),
                    self.getProcessInfoValue(processKey, "ignore_values", index),
                    self.getProcessInfoValue(processKey, "skip_existing", index),
                    self.getProcessInfoValue(processKey, "area_of_interest", index),
                )
                return True
            except BaseException:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False
        elif com == "BPS":
            try:
                self.m_log.Message(
                    "\tBuilding Pyramids and Calculating Statistic for the mosaic dataset : " + self.m_base.m_mdName,
                    self.m_log.const_general_text,
                )
                processKey = "buildpyramidsandstatistics"
                lyrName = "lyr_%s" % str(self.m_base.m_last_AT_ObjectID)
                expression = "OBJECTID >%s" % (str(self.m_base.m_last_AT_ObjectID))
                arcpy.MakeMosaicLayer_management(fullPath, lyrName, expression)
                arcpy.BuildPyramidsandStatistics_management(
                    lyrName,
                    self.getProcessInfoValue(processKey, "include_subdirectories", index),
                    self.getProcessInfoValue(processKey, "build_pyramids", index),
                    self.getProcessInfoValue(processKey, "calculate_statistics", index),
                    self.getProcessInfoValue(processKey, "BUILD_ON_SOURCE", index),
                    self.getProcessInfoValue(processKey, "block_field", index),
                    self.getProcessInfoValue(processKey, "estimate_statistics", index),
                    self.getProcessInfoValue(processKey, "x_skip_factor", index),
                    self.getProcessInfoValue(processKey, "y_skip_factor", index),
                    self.getProcessInfoValue(processKey, "ignore_values", index),
                    self.getProcessInfoValue(processKey, "pyramid_level", index),
                    self.getProcessInfoValue(processKey, "SKIP_FIRST", index),
                    self.getProcessInfoValue(processKey, "resample_technique", index),
                    self.getProcessInfoValue(processKey, "compression_type", index),
                    self.getProcessInfoValue(processKey, "compression_quality", index),
                    self.getProcessInfoValue(processKey, "skip_existing", index),
                )
                arcpy.Delete_management(lyrName)
                return True
            except BaseException:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False
        elif com == "BP":
            try:
                self.m_log.Message(
                    "\tBuilding Pyramid for the mosaic dataset/raster dataset : " + self.m_base.m_mdName, self.m_log.const_general_text
                )
                processKey = "buildpyramids"
                arcpy.BuildPyramids_management(
                    fullPath,
                    self.getProcessInfoValue(processKey, "pyramid_level", index),
                    self.getProcessInfoValue(processKey, "SKIP_FIRST", index),
                    self.getProcessInfoValue(processKey, "resample_technique", index),
                    self.getProcessInfoValue(processKey, "compression_type", index),
                    self.getProcessInfoValue(processKey, "compression_quality", index),
                    self.getProcessInfoValue(processKey, "skip_existing", index),
                )
                return True
            except BaseException:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False
        elif com == "BF":
            try:
                self.m_log.Message("\tRecomputing footprint for the mosaic dataset: " + self.m_base.m_mdName, self.m_log.const_general_text)
                processKey = "buildfootprint"
                isQuery = False
                query = self.getProcessInfoValue(processKey, "where_clause", index)
                if len(query) > 0 and query != "#":
                    isQuery = True
                expression = "OBJECTID >%s" % (str(self.m_base.m_last_AT_ObjectID))
                if isQuery:
                    expression += " AND %s" % (query)
                args = []
                args.append(fullPath)
                args.append(expression)
                args.append(self.getProcessInfoValue(processKey, "reset_footprint", index))
                args.append(self.getProcessInfoValue(processKey, "min_data_value", index))
                args.append(self.getProcessInfoValue(processKey, "max_data_value", index))
                args.append(self.getProcessInfoValue(processKey, "approx_num_vertices", index))
                args.append(self.getProcessInfoValue(processKey, "shrink_distance", index))
                args.append(self.getProcessInfoValue(processKey, "maintain_edges", index))
                args.append(self.getProcessInfoValue(processKey, "skip_derived_images", index))
                args.append(self.getProcessInfoValue(processKey, "update_boundary", index))
                args.append(self.getProcessInfoValue(processKey, "request_size", index))
                args.append(self.getProcessInfoValue(processKey, "min_region_size", index))
                args.append(self.getProcessInfoValue(processKey, "simplification_method", index))
                args.append(self.getProcessInfoValue(processKey, "edge_tolerance", index))
                args.append(self.getProcessInfoValue(processKey, "max_sliver_size", index))
                args.append(self.getProcessInfoValue(processKey, "min_thinness_ratio", index))
                setBuitFootprints = MBase.DynaInvoke("arcpy.BuildFootprints_management", args, None, self.m_log.Message)
                if setBuitFootprints.init() == False:
                    return False
                return setBuitFootprints.invoke()
            except BaseException:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False
        elif com == "BS":
            try:
                self.m_log.Message("\tBuild Seamline for the mosaic dataset: " + self.m_base.m_mdName, self.m_log.const_general_text)
                processKey = "buildseamlines"
                args = []
                args.append(fullPath)
                args.append(self.getProcessInfoValue(processKey, "cell_size", index))
                args.append(self.getProcessInfoValue(processKey, "sort_method", index))
                args.append(self.getProcessInfoValue(processKey, "sort_order", index))
                args.append(self.getProcessInfoValue(processKey, "order_by_attribute", index))
                args.append(self.getProcessInfoValue(processKey, "order_by_base_value", index))
                args.append(self.getProcessInfoValue(processKey, "view_point", index))
                args.append(self.getProcessInfoValue(processKey, "computation_method", index))
                args.append(self.getProcessInfoValue(processKey, "blend_width", index))
                args.append(self.getProcessInfoValue(processKey, "blend_type", index))
                args.append(self.getProcessInfoValue(processKey, "request_size", index))
                args.append(self.getProcessInfoValue(processKey, "request_size_type", index))
                args.append(self.getProcessInfoValue(processKey, "blend_width_units", index))
                args.append(self.getProcessInfoValue(processKey, "area_of_interest", index))
                args.append(self.getProcessInfoValue(processKey, "where_clause", index))
                args.append(self.getProcessInfoValue(processKey, "update_existing", index))
                setBuitSeamlines = MBase.DynaInvoke("arcpy.BuildSeamlines_management", args, None, self.m_log.Message)
                if setBuitSeamlines.init() is False:
                    return False
                return setBuitSeamlines.invoke()
            except BaseException:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False
        elif com == "EMDG":
            self.m_log.Message("\tExport mosaic dataset geometry:" + self.m_base.m_mdName, self.m_log.const_general_text)
            return self.__invokeDynamicFn([fullPath], "exportmosaicdatasetgeometry", "arcpy.ExportMosaicDatasetGeometry_management", index)
        elif com == "EMDI":
            self.m_log.Message("\tExport mosaic dataset items:" + self.m_base.m_mdName, self.m_log.const_general_text)
            return self.__invokeDynamicFn([fullPath], "exportmosaicdatasetitems", "arcpy.ExportMosaicDatasetItems_management", index)
        elif com == "SMDI":
            self.m_log.Message("\tSplit mosaic dataset items:" + self.m_base.m_mdName, self.m_log.const_general_text)
            return self.__invokeDynamicFn([fullPath], "splitmosaicdatasetitems", "arcpy.MergeMosaicDatasetItems_management", index)
        elif com == "SY":
            self.m_log.Message("\tSynchronize mosaic dataset:" + self.m_base.m_mdName, self.m_log.const_general_text)
            return self.__invokeDynamicFn([fullPath], "synchronizemosaicdataset", "arcpy.SynchronizeMosaicDataset_management", index)
        elif com == "CSDD":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            return self.__invokeDynamicFn([], "createimagesddraft", "arcpy.CreateImageSDDraft", index, info=invokeDynamicFnInfo)
        elif com == "STS":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            return self.__invokeDynamicFn([], "stageservice_server", "arcpy.StageService_server", index)
        elif com == "USD":
            self.m_log.Message("\t{}".format(self.commands[com]["desc"]), self.m_log.const_general_text)
            return self.__invokeDynamicFn([], "uploadservicedefinition_server", "arcpy.UploadServiceDefinition_server", index)
        elif com == "CPCSLP":
            self.m_log.Message("\t{}".format(self.commands[com]["desc"]), self.m_log.const_general_text)
            try:
                processKey = "createpointcloudscenelayerpackage"
                arcpy.management.CreatePointCloudSceneLayerPackage(
                    self.getProcessInfoValue(processKey, "in_dataset", index),
                    self.getProcessInfoValue(processKey, "out_slpk", index),
                    arcpy.SpatialReference(int(self.getProcessInfoValue(processKey, "out_coor_system", index))),
                    None,
                    self.getProcessInfoValue(processKey, "attributes", index),
                    self.getProcessInfoValue(processKey, "point_size_m", index),
                    self.getProcessInfoValue(processKey, "xy_max_error_m", index),
                    self.getProcessInfoValue(processKey, "z_max_error_m", index),
                    None,
                    self.getProcessInfoValue(processKey, "scene_layer_version", index),
                )
                return True
            except BaseException:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False
        elif com == "JF":
            try:
                processKey = "joinfield"
                arcpy.JoinField_management(
                    self.getProcessInfoValue(processKey, "in_data", index),
                    self.getProcessInfoValue(processKey, "in_field", index),
                    self.getProcessInfoValue(processKey, "join_table", index),
                    self.getProcessInfoValue(processKey, "join_field", index),
                    self.getProcessInfoValue(processKey, "fields", index),
                )
                return True
            except BaseException:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False

        elif com == "DN":
            try:
                processKey = "definemosaicdatasetnodata"

                lyrName = "lyr_%s" % str(self.m_base.m_last_AT_ObjectID)
                expression = "OBJECTID >%s" % (str(self.m_base.m_last_AT_ObjectID))
                arcpy.MakeMosaicLayer_management(fullPath, lyrName, expression)

                arcpy.DefineMosaicDatasetNoData_management(
                    lyrName,
                    self.getProcessInfoValue(processKey, "num_bands", index),
                    self.getProcessInfoValue(processKey, "bands_for_nodata_value", index),
                    self.getProcessInfoValue(processKey, "bands_for_valid_data_range", index),
                    self.getProcessInfoValue(processKey, "where_clause", index),
                    self.getProcessInfoValue(processKey, "composite_nodata_value", index),
                )
                arcpy.Delete_management(lyrName)
                return True

            except BaseException:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)

        elif com == "IG":
            try:
                processKey = "importgeometry"
                importPath = self.getProcessInfoValue(processKey, "input_featureclass", index)
                const_ig_search_ = ".gdb\\"
                igIndx = importPath.lower().find(const_ig_search_)
                igIndxSep = importPath.find("\\")

                if igIndxSep == igIndx + len(const_ig_search_) - 1:
                    importPath = self.prefixFolderPath(importPath, self.m_base.const_import_geometry_features_path_)

                arcpy.ImportMosaicDatasetGeometry_management(
                    fullPath,
                    self.getProcessInfoValue(processKey, "target_featureclass_type", index),
                    self.getProcessInfoValue(processKey, "target_join_field", index),
                    importPath,
                    self.getProcessInfoValue(processKey, "input_join_field", index),
                )
                return True
            except BaseException:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)

        elif com == "IF":
            processKey = "importfieldvalues"
            try:
                j = 0
                joinTable = self.getProcessInfoValue(processKey, "input_featureclass", index)
                confTableName = os.path.basename(joinTable)

                joinFeildList = [f.name for f in arcpy.ListFields(joinTable)]
                self.log(joinFeildList)
                mlayer = os.path.basename(fullPath) + "layer" + str(j)
                j = j + 1
                arcpy.MakeMosaicLayer_management(fullPath, mlayer)
                self.log("Joining the mosaic dataset layer with the configuration table", self.m_log.const_general_text)
                mlayerJoin = arcpy.AddJoin_management(
                    mlayer + "/Footprint",
                    self.getProcessInfoValue(processKey, "input_join_field", index),
                    joinTable,
                    self.getProcessInfoValue(processKey, "target_join_field", index),
                    "KEEP_ALL",
                )
                for jfl in joinFeildList:
                    if jfl == "Comments" or jfl == "OBJECTID" or jfl == "Dataset_ID":
                        self.log("\t\tvalues exist for the field : " + jfl, self.m_log.const_general_text)
                    else:
                        fieldcal = "AMD_" + self.m_base.m_mdName + "_CAT." + jfl
                        fromfield = "[" + confTableName + "." + jfl + "]"
                        try:
                            arcpy.CalculateField_management(mlayerJoin, fieldcal, fromfield)
                            self.log("\t\tDone calculating values for the Field :" + fieldcal, self.m_log.const_general_text)
                        except BaseException:
                            self.log("Failed to calculate values for the field : " + fieldcal, self.m_log.const_warning_text)
                            self.log(arcpy.GetMessages(), self.m_log.const_warning_text)
                return True
            except BaseException:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)

        elif com == "BB":
            processKey = "buildboundary"
            self.log("Building the boundary " + self.getProcessInfoValue(processKey, "simplification_method", index))
            try:
                arcpy.BuildBoundary_management(
                    fullPath,
                    self.getProcessInfoValue(processKey, "where_clause", index),
                    self.getProcessInfoValue(processKey, "append_to_existing", index),
                    self.getProcessInfoValue(processKey, "simplification_method", index),
                )
                return True
            except BaseException:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False

        # Delete fields
        elif com == "DF":
            processKey = "deletefield"
            try:
                self.log("Deleting fields (%s) " % (self.getProcessInfoValue(processKey, "drop_field", index)))

                arcpy.DeleteField_management(fullPath, self.getProcessInfoValue(processKey, "drop_field", index))
                self.log(arcpy.GetMessages())
                return True
            except BaseException:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False

        elif com == "RP":
            processKey = "repairmosaicdatasetpaths"
            self.log("Repairing mosaic dataset paths ")
            try:
                arcpy.RepairMosaicDatasetPaths_management(
                    fullPath,
                    self.getProcessInfoValue(processKey, "paths_list", index),
                    self.getProcessInfoValue(processKey, "where_clause", index),
                )
                return True
            except BaseException:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False

        elif com == "SS":
            processKey = "setstatistics"
            self.log("Setting MD statistics for:" + fullPath, self.m_log.const_general_text)
            stats_file_ss = self.m_base.getAbsPath(self.getProcessInfoValue(processKey, "stats_file", index))
            if stats_file_ss not in ("#", ""):
                stats_file_ss = self.prefixFolderPath(
                    self.getProcessInfoValue(processKey, "stats_file", index), self.m_base.const_statistics_path_
                )
            try:
                arcpy.SetRasterProperties_management(
                    fullPath,
                    self.getProcessInfoValue(processKey, "data_type", index),
                    self.getProcessInfoValue(processKey, "statistics", index),
                    stats_file_ss,
                    self.getProcessInfoValue(processKey, "nodata", index),
                )
                return True
            except BaseException:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False

        elif com == "CC":
            processKey = "calculatecellsizeranges"
            self.log("Calculating cell ranges for:" + fullPath, self.m_log.const_general_text)
            try:
                arcpy.CalculateCellSizeRanges_management(
                    fullPath,
                    self.getProcessInfoValue(processKey, "where_clause", index),
                    self.getProcessInfoValue(processKey, "do_compute_min", index),
                    self.getProcessInfoValue(processKey, "do_compute_max", index),
                    self.getProcessInfoValue(processKey, "max_range_factor", index),
                    self.getProcessInfoValue(processKey, "cell_size_tolerance_factor", index),
                    self.getProcessInfoValue(processKey, "update_missing_only", index),
                )
                return True
            except BaseException:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False

        elif com == "BO":
            processKey = "buildoverviews"
            self.log("Building overviews for:" + fullPath, self.m_log.const_general_text)
            try:
                arcpy.BuildOverviews_management(
                    fullPath,
                    self.getProcessInfoValue(processKey, "where_clause", index),
                    self.getProcessInfoValue(processKey, "define_missing_tiles", index),
                    self.getProcessInfoValue(processKey, "generate_overviews", index),
                    self.getProcessInfoValue(processKey, "generate_missing_images", index),
                    self.getProcessInfoValue(processKey, "regenerate_stale_images", index),
                )
                return True
            except BaseException:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False

        elif com == "DO":
            processKey = "defineoverviews"
            self.log("Define overviews for:" + fullPath, self.m_log.const_general_text)
            try:
                arcpy.DefineOverviews_management(
                    fullPath,
                    self.getProcessInfoValue(processKey, "overview_image_folder", index),
                    self.getProcessInfoValue(processKey, "in_template_dataset", index),
                    self.getProcessInfoValue(processKey, "extent", index),
                    self.getProcessInfoValue(processKey, "pixel_size", index),
                    self.getProcessInfoValue(processKey, "number_of_levels", index),
                    self.getProcessInfoValue(processKey, "tile_rows", index),
                    self.getProcessInfoValue(processKey, "tile_cols", index),
                    self.getProcessInfoValue(processKey, "overview_factor", index),
                    self.getProcessInfoValue(processKey, "force_overview_tiles", index),
                    self.getProcessInfoValue(processKey, "resampling_method", index),
                    self.getProcessInfoValue(processKey, "compression_method", index),
                    self.getProcessInfoValue(processKey, "compression_quality", index),
                )
                return True
            except BaseException:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False
        elif com == "AI":
            processKey = "addindex"
            self.log("Adding Index:" + fullPath, self.m_log.const_general_text)
            maxValues = len(self.processInfo.processInfo[processKey][index])
            isError = False
            for indx in range(0, maxValues):
                try:
                    arcpy.AddIndex_management(
                        fullPath,
                        self.getProcessInfoValue(processKey, "fields", index, indx),
                        self.getProcessInfoValue(processKey, "index_name", index, indx),
                        self.getProcessInfoValue(processKey, "unique", index, indx),
                        self.getProcessInfoValue(processKey, "ascending", index, indx),
                    )
                except BaseException:
                    self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                    isError = True
            return not isError
        elif com == "CFC":
            processKey = "cachefeatureclass"
            seamlineFC_name = "AMD_" + self.m_base.m_mdName + "_SML"
            seamlineFC_Path = os.path.join(self.m_base.m_geoPath, seamlineFC_name)
            if arcpy.Exists(seamlineFC_Path) == False:
                self.log("Seamline does not exist for the mosaic dataset: " + fullPath, self.m_log.const_general_text)
                return False
            try:
                outCFC = self.getProcessInfoValue(processKey, "out_cache_featureclass", index).replace("\\", "/")
            except Exception as inf:
                self.log(str(inf), self.m_log.const_critical_text)
                return False
            if outCFC.find("/") == -1:
                outCFC = os.path.join(self.m_base.m_geoPath, outCFC)
            if arcpy.Exists(outCFC):
                self.log("Output cache feature class already exists: " + outCFC, self.m_log.const_critical_text)
                return False
            (outCFC_wrk, outCFC_name) = os.path.split(outCFC)
            self.log("Exporting seamline as a feaure class: " + outCFC, self.m_log.const_general_text)
            try:
                arcpy.FeatureClassToFeatureClass_conversion(seamlineFC_Path, outCFC_wrk, outCFC_name, "#", "#", "#")
            except BaseException:
                self.log(
                    "Failed to create the output featue class (%s): (%s)" % (outCFC, arcpy.GetMessages()), self.m_log.const_critical_text
                )
                return False
            try:
                dropFList = ["BlendWidthUnits", "BlendType", "BlendWidth", "ItemHash"]
                sfieldList = arcpy.ListFields(seamlineFC_Path)
                for sfield in sfieldList:
                    if sfield.name.lower() in dropFList:
                        dropFList.remove(sfield.name)
                arcpy.DeleteField_management(outCFC, dropFList)
            except BaseException:
                self.log("Failed to delete the fields: " + arcpy.GetMessages(), self.m_log.const_critical_text)
            catfieldList = []
            catfield = arcpy.ListFields(fullPath)
            for field in catfield:
                catfieldList.append(field.name)
            removelist = [
                "OBJECTID",
                "Shape",
                "Raster",
                "MinPS",
                "MaxPS",
                "HighPS",
                "Category",
                "Tag",
                "GroupName",
                "ProductName",
                "CenterX",
                "CenterY",
                "ZOrder",
                "TypeID",
                "ItemTS",
                "UriHash",
                "Uri",
                "Shape_Length",
                "Shape_Area",
                "SOrder",
                "SLevelPS",
            ]
            importField = list(set(catfieldList) - set(removelist))

            try:
                arcpy.JoinField_management(outCFC, "RasterID", fullPath, "OBJECTID", importField)
            except BaseException:
                self.log("Failed to import metadata fields:" + arcpy.GetMessages(), self.m_log.const_critical_text)
                return False
            return True

        elif com == "CV":
            processKey = "calculatevalues"
            max_CV = len(self.processInfo.processInfo[processKey])
            if index > max_CV - 1:
                self.log(
                    "Wrong index (%s) specified for (%s). Max index is (%s)" % (index, processKey, max_CV - 1),
                    self.m_log.const_critical_text,
                )
                return False
            maxValues = len(self.processInfo.processInfo[processKey][index])
            self.log("Calculate values:" + fullPath, self.m_log.const_general_text)
            isError = False
            for indx in range(0, maxValues):
                isQuery = False
                query = self.getProcessInfoValue(processKey, "query", index, indx)
                lyrName = "lyr_%s_%s" % (
                    str(self.m_base.m_last_AT_ObjectID),
                    datetime.strftime(datetime.now(timezone.utc), "%Y%d%d%H%M%S%f"),
                )
                if query != "#":
                    isQuery = True
                expression = "OBJECTID >%s" % (str(self.m_base.m_last_AT_ObjectID))
                if isQuery:
                    expression += " AND %s" % (query)
                try:
                    arcpy.MakeMosaicLayer_management(fullPath, lyrName)
                    arcpy.SelectLayerByAttribute_management(lyrName, "NEW_SELECTION", expression)
                    lyrName_footprint = lyrName  # + "/Footprint"
                    arcpy.CalculateField_management(
                        lyrName_footprint,
                        self.getProcessInfoValue(processKey, "fieldname", index, indx),
                        self.getProcessInfoValue(processKey, "expression", index, indx),
                        self.getProcessInfoValue(processKey, "expression_type", index, indx),
                        self.getProcessInfoValue(processKey, "code_block", index, indx),
                    )
                except BaseException:
                    self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                    isError = True
                try:
                    # passes for unknown/uncreated layer names
                    arcpy.Delete_management(lyrName)
                except BaseException:
                    self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                    isError = True
            return not isError

        elif com == "CP":
            self.log("Compacting file geodatabase:" + self.m_base.m_geoPath, self.m_log.const_general_text)

            try:
                arcpy.Compact_management(self.m_base.m_geoPath)
                return True
            except BaseException:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False

        elif com == "SE":
            self.log("Set environment variables on index: %s" % (index), self.m_log.const_general_text)

            node = self.m_base.m_doc.getElementsByTagName("Environment")
            if len(node) == 0 or index > len(node) - 1:
                self.log("No environment variables could be found/at index (%s)" % (index), self.m_log.const_warning_text)
                return False
            json = {}
            self.processEnv(node[index].firstChild, 0, json)
            for l in range(0, len(json)):
                p = str(l)
                pIndx = -1
                parent = json[p]["parent"].lower()
                if parent == "environment":
                    pIndx = 0

                key_ = val_ = ""
                key_len_ = len(json[p]["key"])
                for i in range(0, key_len_):
                    typ = json[p]["type"][i]
                    if typ != "p":
                        try:
                            k = json[p]["key"][i]
                            v = json[p]["val"][i]

                            if k == "ClearEnvironment" or k == "ResetEnvironments":  # no use for these yet.
                                continue
                            if pIndx == 0:
                                key_ = k
                                val_ = v.strip()
                                if val_ not in ["", "#"]:
                                    arcpy.env[key_] = val_
                                    self.log("Env[%s]=%s" % (key_, val_), self.m_log.const_general_text)
                                continue
                            else:
                                key_ = json[p]["parent"]
                            val_ += json[p]["val"][i]
                            if i < key_len_ - 1:
                                val_ += " "
                            else:
                                if val_.strip() != "":
                                    arcpy.env[key_] = val_
                                    self.log("Env[%s]=%s" % (key_, val_), self.m_log.const_general_text)
                        except Exception as inst:
                            self.log(str(inst), self.m_log.const_warning_text)
                            continue
            return True  # should unable to set environment variables return False?

        elif com == "MTC":
            mdName = os.path.join(self.m_base.m_geoPath, self.m_base.m_mdName)
            processKey = "managetilecache"
            self.log("Building cache for:" + mdName, self.m_log.const_general_text)
            self.log("Getting tiling Schema : ", self.m_log.const_general_text)
            tileSchemeMtc = self.m_base.getAbsPath(self.getProcessInfoValue(processKey, "import_tiling_scheme", index))
            if tileSchemeMtc != "#" and tileSchemeMtc != "":
                tileSchemeMtc = self.prefixFolderPath(
                    self.getProcessInfoValue(processKey, "import_tiling_scheme", index), os.path.dirname(self.config)
                )
            self.log(tileSchemeMtc, self.m_log.const_general_text)
            try:
                cacheLocation = self.getProcessInfoValue(processKey, "in_cache_location", index)
                if (os.path.exists(cacheLocation)) == False:
                    os.makedirs(cacheLocation)
                arcpy.ManageTileCache_management(
                    cacheLocation,
                    self.getProcessInfoValue(processKey, "manage_mode", index),
                    self.getProcessInfoValue(processKey, "in_cache_name", index),
                    mdName,
                    self.getProcessInfoValue(processKey, "tiling_scheme", index),
                    tileSchemeMtc,
                    self.getProcessInfoValue(processKey, "scales", index),
                    self.getProcessInfoValue(processKey, "area_of_interest", index),
                    self.getProcessInfoValue(processKey, "max_cell_size", index),
                    self.getProcessInfoValue(processKey, "min_cached_scale", index),
                    self.getProcessInfoValue(processKey, "max_cached_scale", index),
                )
                try:
                    if os.path.isfile(tileSchemeMtc):
                        cachepath = os.path.join(
                            self.getProcessInfoValue(processKey, "in_cache_location", index),
                            self.getProcessInfoValue(processKey, "in_cache_name", index),
                        )
                        lodNodesList = returnLevelDetails(os.path.join(cachepath, "conf.xml"))
                        lodNodesList = sorted(lodNodesList, key=lambda k: int(k["level"]))
                        maxLODNode = lodNodesList[-1]
                        maxScale = maxLODNode["scale"]
                        modifyConfProperties(os.path.join(cachepath, "conf.properties"), maxScale)
                except Exception as exp:
                    self.log(str(exp), self.m_log.const_critical_text)
                return True
            except BaseException as exp:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                self.log(str(exp), self.m_log.const_critical_text)
                return False

        elif com == "ETC":
            processKey = "exporttilecache"
            try:
                self.log(
                    "Exporting cache for:" + self.getProcessInfoValue(processKey, "in_target_cache_name", index),
                    self.m_log.const_general_text,
                )
                targetLocation = self.getProcessInfoValue(processKey, "in_target_cache_folder", index)
                os.makedirs(targetLocation)
                arcpy.ExportTileCache_management(
                    self.getProcessInfoValue(processKey, "in_cache_source", index),
                    targetLocation,
                    self.getProcessInfoValue(processKey, "in_target_cache_name", index),
                    self.getProcessInfoValue(processKey, "export_cache_type", index),
                    self.getProcessInfoValue(processKey, "storage_format_type", index),
                    self.getProcessInfoValue(processKey, "scales", index),
                    self.getProcessInfoValue(processKey, "area_of_interest", index),
                )

                return True
            except BaseException:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False

        elif com == "STP":
            processKey = "sharepackage"
            try:
                self.log(
                    "Publishing Tile Package:" + self.getProcessInfoValue(processKey, "in_package", index), self.m_log.const_general_text
                )

                arcpy.SharePackage_management(
                    self.getProcessInfoValue(processKey, "in_package", index),
                    self.getProcessInfoValue(processKey, "username", index),
                    self.getProcessInfoValue(processKey, "password", index),
                    self.getProcessInfoValue(processKey, "summary", index),
                    self.getProcessInfoValue(processKey, "tags", index),
                    self.getProcessInfoValue(processKey, "credits", index),
                    self.getProcessInfoValue(processKey, "public", index),
                    self.getProcessInfoValue(processKey, "groups", index),
                )

                return True
            except BaseException:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False
        elif com == "CRTT":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            fullPath = os.path.join(self.m_base.m_geoPath, "AMD_{0}_ART".format(self.m_base.m_mdName))
            return self.__invokeDynamicFn([fullPath], "clearrastertypetable", "arcpy.DeleteRows_management", index)
        elif com == "CLT":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            fullPath = os.path.join(self.m_base.m_geoPath, "AMD_{0}_LOG".format(self.m_base.m_mdName))
            return self.__invokeDynamicFn([fullPath], "clearlogstable", "arcpy.DeleteRows_management", index)
        elif com == "RP":
            processKey = "repairmosaicdatasetpaths"
            self.log("Repairing mosaic dataset paths ")
            try:
                arcpy.RepairMosaicDatasetPaths_management(
                    fullPath,
                    self.getProcessInfoValue(processKey, "paths_list", index),
                    self.getProcessInfoValue(processKey, "where_clause", index),
                )
                return True
            except BaseException:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False
        elif com == "CCM":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            return self.__invokeDynamicFn([fullPath], "computecameramodel", "arcpy.ComputeCameraModel_management", index)
        elif com == "BSM":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            return self.__invokeDynamicFn([fullPath], "buildstereomodel", "arcpy.BuildStereoModel_management", index)
        elif com == "GPC":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            return self.__invokeDynamicFn([fullPath], "generatepointcloud", "arcpy.GeneratePointCloud_management", index)
        elif com == "IFPC":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            return self.__invokeDynamicFn([], "interpolatefrompointcloud", "arcpy.InterpolateFromPointCloud_management", index)
        elif com == "CRA":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            return self.__invokeDynamicFn(
                [],
                "copyraster",
                "arcpy.CopyRaster_management",
                index,
                info=invokeDynamicFnInfo,  # info = to pass extra args to the fnc '__invokeDynamicFn'
            )
        elif com == "CCSCF":
            self.m_log.Message("\t{}".format(self.commands[com]["desc"]), self.m_log.const_general_text)
            return self.__invokeDynamicFn(
                [], "createcloudstorageconnectionfile", "arcpy.CreateCloudStorageConnectionFile_management", index
            )
        elif com == "DEL":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            return self.__invokeDynamicFn([], "delete", "arcpy.Delete_management", index)
        elif com == "BMI":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            return self.__invokeDynamicFn([fullPath], "buildmultidimensionalinfo", "arcpy.BuildMultidimensionalInfo_management", index)
        elif com == "AMR":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            return self.__invokeDynamicFn([fullPath], "aggregatemultidimensionalraster", "arcpy.ia.AggregateMultidimensionalRaster", index)
        elif com == "COID":
            self.m_log.Message("\t{}".format(self.commands[com]["desc"]), self.m_log.const_general_text)
            return self.__invokeDynamicFn([], "createorientedimagerydataset", "arcpy.oi.CreateOrientedImageryDataset", index)
        elif com == "AITOID":
            self.m_log.Message("\t{}".format(self.commands[com]["desc"]), self.m_log.const_general_text)
            return self.__invokeDynamicFn([], "addimagestoorientedimagerydataset", "arcpy.oi.AddImagesToOrientedImageryDataset", index)
        elif com == "AIFCIT":
            self.m_log.Message("\t{}".format(self.commands[com]["desc"]), self.m_log.const_general_text)
            return self.__invokeDynamicFn([], "addimagesfromcustominputtype", "arcpy.oi.AddImagesFromCustomInputType", index)
        elif com == "BOIF":
            self.m_log.Message("\t{}".format(self.commands[com]["desc"]), self.m_log.const_general_text)
            return self.__invokeDynamicFn([], "buildorientedimageryfootprint", "arcpy.oi.BuildOrientedImageryFootprint", index)
        elif com == "GSFOID":
            self.m_log.Message("\t{}".format(self.commands[com]["desc"]), self.m_log.const_general_text)
            return self.__invokeDynamicFn(
                [], "generateservicefromorientedimagerydataset", "arcpy.oi.GenerateServiceFromOrientedImageryDataset", index
            )
        elif com == "UOIDP":
            self.m_log.Message("\t{}".format(self.commands[com]["desc"]), self.m_log.const_general_text)
            return self.__invokeDynamicFn(
                [], "updateorientedimagerydatasetproperties", "arcpy.oi.UpdateOrientedImageryDatasetProperties", index
            )
        elif com == "ACUC":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            return self.__invokeDynamicFn([], "analyzechangesusingccdc", "arcpy.ia.AnalyzeChangesUsingCCDC", index)
        elif com == "DCUCAR":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            return self.__invokeDynamicFn([], "detectchangeusingchangeanalysis", "arcpy.ia.DetectChangeUsingChangeAnalysis", index)
        elif com == "FAS":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            return self.__invokeDynamicFn([], "findargumentstatistics", "arcpy.ia.FindArgumentStatistics", index)
        elif com == "GMA":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            return self.__invokeDynamicFn([], "generatemultidimensionalanomaly", "arcpy.ia.GenerateMultidimensionalAnomaly", index)
        elif com == "CF":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            return self.__invokeDynamicFn([fullPath], "computefiducials", "arcpy.ComputeFiducials_management", index)
        elif com == "UIO":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            return self.__invokeDynamicFn([fullPath], "updateinteriororientation", "arcpy.UpdateInteriorOrientation_management", index)
        elif com == "EFACP":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            return self.__invokeDynamicFn(
                [fullPath], "exportframeandcameraparameters", "arcpy.ExportFrameAndCameraParameters_management", index
            )
        elif com == "GBAR":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            return self.__invokeDynamicFn(
                [fullPath], "generateblockadjustmentreport", "arcpy.GenerateBlockAdjustmentReport_management", index
            )
        elif com == "GTR":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            return self.__invokeDynamicFn([], "generatetrendraster", "arcpy.ia.GenerateTrendRaster", index)
        elif com == "PUTR":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            return self.__invokeDynamicFn([], "predictusingtrendraster", "arcpy.ia.PredictUsingTrendRaster", index)
        elif com == "RR":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            processKey = "registerraster"
            try:
                query = self.m_base.getXMLXPathValue("Application/Workspace/MosaicDataset/Processes/RegisterRaster/query", "query")
            except Exception as exp:
                self.log(str(exp), self.m_log.const_critical_text)
                self.log("Setting query value as #", self.m_log.const_warning_text)
                query = "#"
            if query == "#":  # run the tool on the entire mosaic dataset
                return self.__invokeDynamicFn([fullPath], "registerraster", "arcpy.RegisterRaster_management", index)
            else:
                with arcpy.da.SearchCursor(fullPath, ["OBJECTID", "Name"], where_clause=query) as sc:  # pylint:disable=E1101
                    for row in sc:
                        try:
                            rasteritem = os.path.join(fullPath, f"OBJECTID={row[0]}")
                            status = self.__invokeDynamicFn([rasteritem], "registerraster", "arcpy.RegisterRaster_management", index)
                            if not status:
                                self.log(f"Failed for {row[1]}", self.m_log.const_critical_text)
                            else:
                                self.log(f"Successful for {row[1]}", self.m_log.const_general_text)
                        except Exception as exp:
                            self.log(f"Failed for {row[1]}/{exp}", self.m_log.const_critical_text)
                            continue
                del sc
                return True
        elif com == "CPUDL":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            return self.__invokeDynamicFn([], "classifypixelsusingdeeplearning", "arcpy.ia.ClassifyPixelsUsingDeepLearning", index)
        elif com == "DOUDL":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            return self.__invokeDynamicFn([], "detectobjectsusingdeeplearning", "arcpy.ia.DetectObjectsUsingDeepLearning", index)
        elif com == "COUDL":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            return self.__invokeDynamicFn([], "classifyobjectsusingdeeplearning", "arcpy.ia.ClassifyObjectsUsingDeepLearning", index)
        elif com == "EFUAIM":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            processKey = "extractfeaturesusingaimodels"
            in_raster = self.getProcessInfoValue(processKey, "in_raster", index)
            output_path = self.getProcessInfoValue(processKey, "out_location", index)
            out_prefix = self.getProcessInfoValue(processKey, "out_prefix", index)
            if in_raster == "#":
                in_raster = fullPath
            if output_path == "#":
                output_path = f"{fullPath}{processKey}"
            if out_prefix == "#":
                out_prefix = f"{fullPath}{processKey}"
            return self.__invokeDynamicFn(
                [
                    in_raster,
                    self.getProcessInfoValue(processKey, "mode", index),
                    output_path,
                    out_prefix,
                    self.getProcessInfoValue(processKey, "area_of_interest", index),
                    self.getProcessInfoValue(processKey, "pretrained_models", index),
                    self.getProcessInfoValue(processKey, "additional_models", index),
                    self.getProcessInfoValue(processKey, "confidence_threshold", index),
                    self.getProcessInfoValue(processKey, "save_intermediate_output", index),
                    self.getProcessInfoValue(processKey, "test_time_augmentation", index),
                    self.getProcessInfoValue(processKey, "buffer_distance", index),
                    self.getProcessInfoValue(processKey, "extend_length", index),
                    self.getProcessInfoValue(processKey, "smoothing_tolerance", index),
                    self.getProcessInfoValue(processKey, "dangle_length", index),
                    self.getProcessInfoValue(processKey, "in_road_features", index),
                    self.getProcessInfoValue(processKey, "road_buffer_width", index),
                    self.getProcessInfoValue(processKey, "regularize_parcels", index),
                    self.getProcessInfoValue(processKey, "post_processing_workflow", index),
                    self.getProcessInfoValue(processKey, "out_features", index),
                    self.getProcessInfoValue(processKey, "parcel_tolerance", index),
                    self.getProcessInfoValue(processKey, "regularization_method", index),
                    self.getProcessInfoValue(processKey, "poly_tolerance", index),
                ],
                processKey,
                "arcpy.geoai.ExtractFeaturesUsingAIModels",
                index,
            )
        elif com == "GRFRF":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            return self.__invokeDynamicFn(
                [], "generaterasterfromrasterfunction", "arcpy.management.GenerateRasterFromRasterFunction", index
            )
        elif com == "TF":
            try:
                self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
                processKey = "transferfiles"
                inacspath_update = []
                inacspath = self.getProcessInfoValue(processKey, "input_paths", index)
                inacspath_split = inacspath.split(";")
                for inacsfile in inacspath_split:
                    if (inacsfile.find(".acs")) > -1 and (inacsfile.find("/") == -1):
                        inacspath_update.append(os.path.join(self.m_base.const_workspace_path_, "Parameter/ACSFiles", inacsfile))
                    else:
                        inacspath_update.append(inacsfile)
                inacspath = ";".join(inacspath_update)
                outpath = self.getProcessInfoValue(processKey, "output_folder", index)
                if (outpath.find(".acs")) > -1 and (outpath.find("/") == -1):
                    outpath = os.path.join(self.m_base.const_workspace_path_, "Parameter/ACSFiles", outpath)
                return self.__invokeDynamicFn(
                    [inacspath, outpath, self.getProcessInfoValue(processKey, "file_filter", index)],
                    processKey,
                    "arcpy.management.TransferFiles",
                    index,
                )

            except BaseException as exp:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False
        elif com == "ZSAT":
            self.m_log.Message("\t{}:{}".format(self.commands[com]["desc"], self.m_base.m_mdName), self.m_log.const_general_text)
            return self.__invokeDynamicFn([], "zonalstatisticsastable", "arcpy.ia.ZonalStatisticsAsTable", index)
        else:
            # The command could be a user defined function externally defined
            # in the module (MDCS_UC.py). Let's invoke it.
            data = self.m_base.m_data
            data["useResponse"] = False  # Previous w/f cmd output mode is disabled.
            ret_status = self.m_base.invoke_user_function(com, data)
            use_response = "useResponse" in data and data["useResponse"]
            response = {}
            if use_response:
                response.update({"response": data["response"]})
                if "code" in data:
                    # Optional, any user defined code regardless of the
                    # function status.
                    response["code"] = data["code"]
                response["status"] = data["response"].get("status", False)  # Overall function status, i.e. True or False
                if not self.m_base.getBooleanValue(response["status"]):
                    return response
            if not ret_status:
                return False
            if self.config and not self.m_base.is_builtin_event(com):
                parent_root = "Application/Workspace"
                mosaic_dataset = self.m_base.getXMLXPathValue(f"{parent_root}/MosaicDataset/Name", "Name")
                workspace = self.m_base.getXMLXPathValue(f"{parent_root}/WorkspacePath", "WorkspacePath")
                geo_db = self.m_base.getXMLXPathValue(f"{parent_root}/Geodatabase", "Geodatabase")
                const_geodatabase_ext = self.m_base.const_geodatabase_ext.lower()
                geo_gdb_lower = geo_db.lower()
                mk_geo_path = "{}{}".format(
                    os.path.join(workspace, geo_db),
                    (
                        const_geodatabase_ext
                        if (not geo_gdb_lower.endswith(const_geodatabase_ext) and not geo_gdb_lower.endswith("sde"))
                        else ""
                    ),
                ).replace("\\", "/")
                self.m_base.m_geodatabase = geo_db
                self.m_base.m_workspace = workspace
                data["mosaicdataset"] = self.m_base.m_mdName = mosaic_dataset
                data["workspace"] = self.m_base.m_geoPath = mk_geo_path
                # Update internal data structures if user function has
                # modifield the in-memory xml dom.
                ret_status = True if not self.config else self.processInfo.init(self.config)
                if not ret_status:
                    self.m_log.Message(f"Unable to re-initialize the config ({self.config})", self.m_log.const_critical_text)
            return response if use_response and ret_status else ret_status
        return False  # main function body return, no matching command found!

    commands = {
        "CM": {"desc": "Create a new mosaic dataset.", "fnc": executeCommand},
        "CR": {"desc": "Create new referenced mosaic dataset.", "fnc": executeCommand},
        "AF": {"desc": "Add fields.", "fnc": executeCommand},
        "AR": {"desc": "Add rasters/data to a mosaic dataset.", "fnc": executeCommand},
        "BF": {"desc": "Build footprint.", "fnc": executeCommand},
        "JF": {"desc": "Join the content of two tables based on a common attribute field.", "fnc": executeCommand},
        "BS": {"desc": "Build Seamlines.", "fnc": executeCommand},
        "BP": {"desc": "Build Pyramid.", "fnc": executeCommand},
        "ANCP": {"desc": "Analyze Control Points.", "fnc": executeCommand},
        "APCP": {"desc": "Append Control Points.", "fnc": executeCommand},
        "ABA": {"desc": "Apply Block Adjustment.", "fnc": executeCommand},
        "CBA": {"desc": "Compute Block Adjustment.", "fnc": executeCommand},
        "CCP": {"desc": "Compute Control Points.", "fnc": executeCommand},
        "CTP": {"desc": "Compute Tie Points.", "fnc": executeCommand},
        "AMDS": {"desc": "Alter Mosaic Dataset Schema.", "fnc": executeCommand},
        "AMD": {"desc": "Analyze Mosaic Dataset.", "fnc": executeCommand},
        "BMDIC": {"desc": "Build Mosaic Dataset Item Cache.", "fnc": executeCommand},
        "CDA": {"desc": "Compute Dirty Area.", "fnc": executeCommand},
        "GEA": {"desc": "Generate Exclude Area.", "fnc": executeCommand},
        "CS": {"desc": "Calculate Statistics.", "fnc": executeCommand},
        "RP": {"desc": "Repair mosaic dataset paths", "fnc": executeCommand},
        "CBMD": {"desc": "Color balance mosaic dataset.", "fnc": executeCommand},
        "RRFMD": {"desc": "Remove Rasters from Mosaic ataset.", "fnc": executeCommand},
        "DMD": {"desc": "Delete Mosaic dataset.", "fnc": executeCommand},
        "MMDI": {"desc": "Merge Mosaic dataset items.", "fnc": executeCommand},
        "BPS": {"desc": "Build pyramid and Statistics.", "fnc": executeCommand},
        "ERF": {"desc": "Edit raster function.", "fnc": executeCommand},
        "DN": {"desc": "Define no data values.", "fnc": executeCommand},
        "SP": {"desc": "Set mosaic dataset properties.", "fnc": executeCommand},
        "IG": {"desc": "Import mosaic dataset geometry.", "fnc": executeCommand},
        "DF": {"desc": "Delete field.", "fnc": executeCommand},
        "IF": {"desc": "Import field values/calculate fields.", "fnc": executeCommand},
        "BB": {"desc": "Build boundary.", "fnc": executeCommand},
        "SS": {"desc": "Set statistics for a raster or mosaic dataset.", "fnc": executeCommand},
        "CC": {"desc": "Computes the minimum and maximum cell sizes for the rasters in a mosaic dataset.", "fnc": executeCommand},
        "BO": {"desc": "Defines and generates overviews for a mosaic dataset.", "fnc": executeCommand},
        "DO": {"desc": "Defines the tiling schema and properties of the preprocessed raster datasets.", "fnc": executeCommand},
        "AI": {"desc": "Adds attribute index on the mosaic dataset.", "fnc": executeCommand},
        "RI": {"desc": "Removes attribute index on the mosaic dataset.", "fnc": executeCommand},
        "CFC": {"desc": "Create cache feature class.", "fnc": executeCommand},
        "CV": {"desc": "Calculate mosaic dataset values.", "fnc": executeCommand},
        "CP": {"desc": "Compact file geodatabase.", "fnc": executeCommand},
        "SY": {"desc": "Synchronize mosaic dataset.", "fnc": executeCommand},
        "SE": {"desc": "Set environment variables.", "fnc": executeCommand},
        "MTC": {"desc": "Manage Tile Cache.", "fnc": executeCommand},
        "ETC": {"desc": "Export Tile Cache.", "fnc": executeCommand},
        "STP": {"desc": "Share Package.", "fnc": executeCommand},
        "EMDG": {"desc": "Export mosaic dataset geometry.", "fnc": executeCommand},
        "EMDI": {"desc": "Export mosaic dataset items.", "fnc": executeCommand},
        "SMDI": {"desc": "Split mosaic dataset items.", "fnc": executeCommand},
        "CSDD": {"desc": "Create an image service definition draft file.", "fnc": executeCommand},
        "STS": {"desc": "Stages a service definition.", "fnc": executeCommand},
        "USD": {"desc": "Uploads and publishes a service definition to a specified server.", "fnc": executeCommand},
        "CRTT": {"desc": "Delete records from the Raster Type table.", "fnc": executeCommand},
        "CLT": {"desc": "Delete records from the Logs table.", "fnc": executeCommand},
        "CCM": {"desc": "Compute Camera Model.", "fnc": executeCommand},
        "BSM": {"desc": "Build Stereo Model.", "fnc": executeCommand},
        "GPC": {"desc": "Generate Point Cloud.", "fnc": executeCommand},
        "IFPC": {"desc": "Interpolate From Point Cloud.", "fnc": executeCommand},
        "CRA": {"desc": "Copy Raster.", "fnc": executeCommand},
        "DEL": {"desc": "Delete Mosaic.", "fnc": executeCommand},
        "RR": {"desc": "Register Raster.", "fnc": executeCommand},
        "BMI": {"desc": "Build Multidimensional Info.", "fnc": executeCommand},
        "AMR": {"desc": "Aggregate Multidimensional Raster.", "fnc": executeCommand},
        "ACUC": {"desc": "Analyze Changes Using CCDC.", "fnc": executeCommand},
        "DCUCAR": {"desc": "Detect Change Using Change Analysis Raster.", "fnc": executeCommand},
        "FAS": {"desc": "Find Argument Statistics.", "fnc": executeCommand},
        "GMA": {"desc": "Generate Multidimensional Anomaly.", "fnc": executeCommand},
        "CF": {"desc": "Compute Fiducials.", "fnc": executeCommand},
        "UIO": {"desc": "Update Interior Orientation.", "fnc": executeCommand},
        "EFACP": {"desc": "Export Frame And Camera Parameters.", "fnc": executeCommand},
        "GBAR": {"desc": "Generate Block Adjustment Report.", "fnc": executeCommand},
        "GTR": {"desc": "Generate Trend Raster.", "fnc": executeCommand},
        "PUTR": {"desc": "Predict Using Trend Raster.", "fnc": executeCommand},
        "CPCSLP": {
            "desc": "Creates a point cloud scene layer package (.slpk file) from LAS, zLAS, LAZ, or LAS dataset input.",
            "fnc": executeCommand,
        },
        "CPUDL": {"desc": "Gives Segmented image as output using Deep Learning", "fnc": executeCommand},
        "COUDL": {"desc": "Classifying Objects using Deep Learning", "fnc": executeCommand},
        "DOUDL": {"desc": "Detecing Objects using Deep Learning", "fnc": executeCommand},
        "EFUAIM": {"desc": "Extract Features Using AI Models", "fnc": executeCommand},
        "GRFRF": {"desc": "Generate Raster From Raster Function", "fnc": executeCommand},
        "CCSCF": {"desc": "Create Cloud Storage Connection File", "fnc": executeCommand},
        "COID": {"desc": "Create Oriented Imagery Dataset", "fnc": executeCommand},
        "GSFOID": {"desc": "Generate Service From Oriented Imagery Dataset", "fnc": executeCommand},
        "BOIF": {"desc": "Build Oriented Imagery Footprint", "fnc": executeCommand},
        "AIFCIT": {"desc": "Add Images From Custom Input Type", "fnc": executeCommand},
        "AITOID": {"desc": "Add Images To Oriented Imagery Dataset", "fnc": executeCommand},
        "UOIDP": {"desc": "Update Oriented Imagery Dataset Properties", "fnc": executeCommand},
        "TF": {"desc": "Transfer Files", "fnc": executeCommand},
        "ZSAT": {"desc": "Zonal Statistics As Table", "fnc": executeCommand},
    }

    # mapping of config/component paths.
    base_path_ = scriptPath + "/"
    com_locations = {
        "CreateMD": {
            "pyc": base_path_ + "CreateMD/",
        },
        "AddFields": {
            "pyc": base_path_ + "AddFields/",
        },
        "AddRasters": {
            "pyc": base_path_ + "AddRasters/",
        },
        "SetMDProperties": {
            "pyc": base_path_ + "SetMDProperties/",
        },
        "CreateRefMD": {
            "pyc": base_path_ + "CreateRefMD/",
        },
        "ProcessInfo": {
            "pyc": base_path_ + "ProcessInfo/",
        },
        "Base": {
            "pyc": base_path_ + "Base/",
        },
    }

    # update environment path to include where components reside.
    sys.path.append(com_locations["CreateMD"]["pyc"])
    sys.path.append(com_locations["AddFields"]["pyc"])
    sys.path.append(com_locations["AddRasters"]["pyc"])
    sys.path.append(com_locations["CreateRefMD"]["pyc"])
    sys.path.append(com_locations["SetMDProperties"]["pyc"])
    sys.path.append(com_locations["ProcessInfo"]["pyc"])
    sys.path.append(com_locations["Base"]["pyc"])

    def getProcessInfoValue(self, process, key, index=0, indx=-1):
        """Get the corresponding value from the {process}/{key} in the config file."""
        if index > len(self.processInfo.processInfo[process]) - 1:
            err_msg = f"Err. Invalid command index ({index})."
            self.log(err_msg, self.const_critical_text)
            raise IndexError(err_msg)
        if indx > -1:  # handle process info on keys [addindex, calculatevalues]
            if key in self.processInfo.processInfo[process][index][indx].keys():
                return self.processInfo.processInfo[process][index][indx][key]
            return "#"
        if key in self.processInfo.processInfo[process][index].keys():
            return self.processInfo.processInfo[process][index][key]
        return "#"

    def run(self, com):
        """run w/f command chain, using the '+' char as the command seperator."""
        Upd_Chain = "upd_chain"
        com_ = com
        if com_.upper() == self.const_cmd_default_text.upper():
            try:
                # gets command defaults.
                com_ = self.getXMLNodeValue(self.m_base.m_doc, "Command")
                self.log(f"Using default command(s):{com_}")
            except BaseException:
                self.log(f"Err. Reading input config file:{self.config}\nQuitting...", self.const_critical_text)
                self.__cleanup()
                return False
            if len(com_.strip()) == 0:
                self.log("Err. Empty command.", self.const_critical_text)
                self.__cleanup()
                return False
        # ends
        cur_step = "/"
        if self.live_progress:
            cur_step = self.m_base.m_data["__user"].get("__step__", "root")
        self.log(f"Processing command(s):{com_.upper()}", self.const_general_text)
        aryCmds = com_.split("+")
        if self.m_base.EVT_ON_START in self.m_base.on_evnt_args:
            del self.m_base.on_evnt_args[self.m_base.on_evnt_args.index(self.m_base.EVT_ON_START)]
            if self.m_base.isUser_Function(self.m_base.EVT_ON_START):
                aryCmds.insert(0, self.m_base.EVT_ON_START)
        if self.on_exit():
            aryCmds.append(self.m_base.EVT_ON_EXIT)
        cmdResults = []
        cmd_len = len(aryCmds)
        self.perc_range = PERC_MAX / cmd_len
        while aryCmds:
            command = aryCmds.pop(0)
            _info = {"step": f"{cur_step}", "command": f"{command}"}
            if self.live_progress:
                _info.update({"msg_type": "CMD", "mod": MOD_NAME})
                self.send_message(_info, self.job_id, RT_CUR_CMD)
            ucCommand = command
            command = command.upper()
            is_user_cmd = False
            cmd = "".join(ch for ch in command if ch in (ascii_letters + "_"))
            index = 0
            if len(command) > len(cmd):
                try:
                    index = int(command[len(cmd) :])
                except BaseException:
                    self.log(f"Command/Err: Invalid command index:{command}", self.const_warning_text)
                    # catch any float values entered, e.t.c
            if cmd not in self.commands:
                if self.m_base.isUser_Function(ucCommand):
                    try:
                        self.commands[ucCommand] = {}
                        self.commands[ucCommand]["desc"] = f"User defined command ({ucCommand})"
                        # can't use self.executeCommand directly here. Need to
                        # check.
                        self.commands[ucCommand]["fnc"] = self.commands["CM"]["fnc"]
                        # preserve user defined function case.
                        cmd = ucCommand
                        is_user_cmd = True
                    except BaseException:
                        self.log(f"Unabled to add user defined function/command ({ucCommand}) to command chain.", self.const_warning_text)
                        break  # prevent further processing.
                else:
                    self.log(f"Command/Err: Unknown command:{cmd}", self.const_warning_text)
                    cmdResults.append({"cmd": cmd, "value": False, "cmd_type": UC_CMD_TYPE_UNKNOWN})
                    if aryCmds and aryCmds[-1] == self.m_base.EVT_ON_EXIT:
                        aryCmds = [self.m_base.EVT_ON_EXIT]
                        continue
                    break
            indexed_cmd = False if index == 0 else True
            cat_cmd = f"{cmd}{'' if not indexed_cmd else index}"
            if self.isLog():
                self.m_log.CreateCategory(cat_cmd)
            is_event = self.m_base.is_builtin_event(cat_cmd)
            msg_cmd = f"Event/{cat_cmd}" if is_event else f"Command:{cat_cmd}->{self.commands[cmd]['desc']}"
            self.log(msg_cmd, self.const_general_text)
            if indexed_cmd:
                self.log(f"Using parameter values at index ({index})", self.const_general_text)
            success = "OK"
            if cmd == self.m_base.EVT_ON_EXIT:
                self.m_base.m_data["cmd_results"] = cmdResults
            response = self.commands[cmd]["fnc"](self, cmd, index)
            respVals = {"cmd": cmd}
            status = False
            if isinstance(response, bool):
                status = response
            elif isinstance(response, dict):
                if "response" in response and response["response"] and isinstance(response["response"], dict):
                    response = response["response"]
                if "status" in response:
                    status = self.m_base.getBooleanValue(response["status"])
                if "output" in response:
                    respVals["output"] = response["output"]
            respVals["value"] = status
            respVals["cmd_type"] = UC_CMD_TYPE_EVENT if is_event else UC_CMD_TYPE_USER
            cmdResults.append(respVals)
            if not status:
                success = "Failed!"
            _info.update({"msg_type": "STS", "status": success, "mod": MOD_NAME})
            self.send_message(_info, self.job_id, RT_INF)
            if self.isLog():
                self.m_log.CloseCategory()
            if cmd == self.m_base.EVT_ON_EXIT:
                break
            if not status and (  # do not continue with any failures in following command list or any user function.
                cmd in ["AR", "CM", "CBA", "ABA"] or is_user_cmd
            ):
                if aryCmds and aryCmds[-1] == self.m_base.EVT_ON_EXIT:
                    aryCmds = [self.m_base.EVT_ON_EXIT]
                    continue
                break
            self.cmd_pos += 1
            if isinstance(response, dict) and Upd_Chain in response and isinstance(response[Upd_Chain], list):
                aryCmds[:] = response[Upd_Chain]
        self.__cleanup()
        return cmdResults

    def init(self, conf, info):
        """init"""
        if self.m_base is None:
            return False
        logger.addHandler(LogHandler(self.logging_filter))
        self.config = conf  # configuration/XML template
        self.userInfo = info  # callback information for commands /e.t.c.
        self.log_csv_filepath = self.m_base.m_log.make_log_filename()
        self.msg_codes = ["INF", "WRN", "ERR", "STS", "CMD", "PMO"]
        if not self.log_csv_filepath[-4:].lower().endswith(".csv"):
            self.log_csv_filepath = self.log_csv_filepath[:-3] + "csv"
        try:
            self.m_base.m_doc = minidom.parse(self.config) if conf else None
            self.live_progress = True
            self.session = info["__user"].get("__wp__", None)
            self.job_id = info["__user"].get("__job__", "0000")
            (ret, msg) = self.m_base.init()
            if not ret:
                if msg in (self.m_base.const_init_ret_version, self.m_base.const_init_ret_sde, self.m_base.const_init_ret_patch):
                    return False
                raise ValueError
            UserArgs = "__user"
            # removes any previously initialized user-args data.
            self.m_base.m_data[UserArgs] = {}
            self.m_base.m_data[UserArgs] = self.userInfo[UserArgs]
            del self.userInfo[UserArgs]
        except Exception as e:
            self.log(f"Unable to read the input parameter file ({self.config})\n{e}\nQuitting...", self.const_critical_text)
            return False
        from ProcessInfo.ProcessInfo import ProcessInfo
        self.processInfo = ProcessInfo(self.m_base)
        if conf:
            bSuccess = self.processInfo.init(self.config)
            if not bSuccess:
                self.log(f"Unable to process the parameter file ({self.config})", self.const_critical_text)
                return False
            bSuccess = self.processInfo.hasProcessInfo
            self.log("Using template:" + self.config, self.const_general_text)
        self.cmd_pos = 0
        return True

    def log_stream(self, msg_type, msg):
        """The callback to receive internal log messages plus format the log text before sending to MDCS RTS."""
        strm = msg[0] if isinstance(msg, list) else msg
        if isinstance(strm, int):
            strm = msg_type
        strm = ":".join(strm.split(":")[1:])
        if self.live_progress:
            mod_print = self.get_callstack_fnc_names()
            _info = {"msg_type": msg_type, "msg": strm, "mod": mod_print}
            self.send_message(_info, self.job_id, RT_INF)
        return True

    def logging_filter(self, record):
        """Convert logging/messages to RTS equivalent"""
        severity: int = MSG_INF
        if record.levelname == "WARNING":
            severity = MSG_WRN
        elif record.levelname == "CRITICAL":
            severity = MSG_ERR
        _info = {
            "msg_type": ["INF", "WRN", "ERR"][severity],
            "msg": record.getMessage(),
            "mod": CALLSTACK_SEP.join(self.get_callstack_fnc_names().split(CALLSTACK_SEP)[:2]),
        }  # omit ->emit->(this->method name)
        self.send_message(_info, self.job_id, RT_INF)

    def send_message(self, msg_body, job_id, rt_code):
        """Send a message using the job_id and the RT message codes that are defined using the RT prefix constants."""
        if (not self.log_csv_filepath or 
            not self.m_log.is_log_CSV()):
            return False
        try:
            with open(self.log_csv_filepath, "a+", encoding="utf-8") as writer:
                msg_code = MSG_INF  # INF
                mod = ""
                if isinstance(msg_body, dict):
                    if "msg_type" in msg_body:
                        msg_type = msg_body["msg_type"]
                        if msg_type in self.msg_codes:
                            msg_code = self.msg_codes.index(msg_type)
                            # disable double values in out-stream
                            del msg_body["msg_type"]
                    if "mod" in msg_body:
                        mod = msg_body["mod"]
                        del msg_body["mod"]
                format_msg = self.add_message(
                    msg_body,
                    msg_code,
                    job_id=job_id,
                    mod=mod,
                )               
                writer.write(f"{format_msg}")
        except IOError as exp_log:
            print(f"Err. {exp_log}")
            return False
        return True

    def close(self):
        """Send the (RT_WF_END), i.e. end of w/f message to RTS."""
        _info = {"msg": "bye", "mod": MOD_NAME}
        self.send_message(_info, self.job_id, RT_WF_END)
        return True

    @property
    def is_rts_connected(self):
        """To test if rts service is connected to stream logs."""
        return None

    def __cleanup(self):
        """cleaup internals"""
        self.close()
        return True

    def on_exit(self):
        """_OnExit event that gets fired at the end of the w/f"""
        if self.m_base.EVT_ON_EXIT in self.m_base.on_evnt_args:
            del self.m_base.on_evnt_args[self.m_base.on_evnt_args.index(self.m_base.EVT_ON_EXIT)]
            if self.m_base.isUser_Function(self.m_base.EVT_ON_EXIT):
                return True
        return False

    def get_callstack_fnc_names(self):
        """fetch function names leading upto the logging text"""
        footprint = stack()
        fn_names = []
        for page in footprint:
            filename = page.filename
            if any(filename.endswith(x) for x in ["solutionsLib.py", "MDCS_UC.py", "MDCS.py"]):  # MDCS core source filenames
                fn_names.append(page.function)
        mdcsuc_sig = "executeCommand"
        mod_print = "MDCS" if len(fn_names) == 2 and fn_names[1] == "main" else MOD_NAME
        if mdcsuc_sig in fn_names:
            fn_names = fn_names[: fn_names.index(mdcsuc_sig)]
            fn_names.pop(0)
            fn_names.reverse()
            fn_names.pop(-1)
            fn_names.insert(0, "MDCS_UC" if fn_names else MOD_NAME)
            mod_print = f"{CALLSTACK_SEP.join(fn_names)}"
        return mod_print

    def add_message(self, msg, code=MSG_INF, **kwargs):
        """add messge to the session wf_store"""
        if JOB_ID not in kwargs:
            return False
        job_id = kwargs[JOB_ID]
        msg_mod = kwargs.get("mod", "")
        msg_type = self.msg_codes[MSG_INF if code < MSG_INF or code > len(self.msg_codes) else code]
        gmt_time = datetime.now(timezone.utc).strftime(ISO_DT)
        if msg_mod == "":
            check = 0
        return f"{gmt_time}{FLDS_SEP}{job_id}{FLDS_SEP}{msg_type}{FLDS_SEP}[{msg_mod}]{FLDS_SEP}{msg}\n"

