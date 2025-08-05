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
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# -------------------------------------------------------------------------------
# Name:  CreateMD.py
# Description:  Creates source mosaic datasets.
# Version:  20250418
# Requirements:  ArcGIS 10.1 SP1
# Optional Arguments: <optional args if any>
# Usage: CreateMD.py [arguments]
# Author:  Esri Imagery Workflows team
# -------------------------------------------------------------------------------
#!/usr/bin/env python

import os
import arcpy
from Base.Base import Base as CBase


class CreateMD(CBase):
    """Create MD class."""

    def __init__(self, base):
        self.srs = ""
        self.pixel_type = ""
        self.product_definition = ""
        self.num_bands = ""
        self.product_band_definitions = ""
        self.setLog(base.m_log)
        self.m_base = base

    def createGeodataBase(self):
        """create GDB"""
        resp = {"status": False}
        if self.m_base.m_IsSDE:  # MDCS doesn't create new SDE connections and assumes .SDE connection passed on exists @ the server
            return self.m_base._updateResponse(resp, status=True)
        # create output workspace if missing.
        if os.path.exists(self.m_base.m_workspace) is False:
            try:
                os.makedirs(self.m_base.m_workspace)
            except BaseException:
                self.log(f"Failed to create folder: {self.m_base.m_workspace}\n{arcpy.GetMessages()}", self.const_critical_text)
                return resp
        # create Geodatabase
        try:
            self.log(f"Creating Geodatabase: ({self.m_base.m_geoPath})", self.const_general_text)
            if not os.path.exists(self.m_base.m_geoPath):
                arcpy.CreateFileGDB_management(self.m_base.m_workspace, self.m_base.m_gdbName)
            else:
                self.log("\t000258: File geodatabase already exists!", self.const_warning_text)
            return self.m_base._updateResponse(resp, status=True, output=self.m_base.m_geoPath)
        except Exception as e:
            self.log(f"\t{e}", self.const_critical_text)
        return resp

    def createMD(self):
        """Create MD"""
        self.log("Creating source mosaic datasets:", self.const_general_text)
        resp = {"status": False}
        try:
            mdPath = os.path.join(self.m_base.m_geoPath, self.m_base.m_mdName)
            if arcpy.Exists(mdPath):
                return self.m_base._updateResponse(resp, status=True, output=mdPath)
            self.log(f"\t{self.m_base.m_mdName}", self.const_general_text)
            arcpy.CreateMosaicDataset_management(
                self.m_base.m_geoPath,
                self.m_base.m_mdName,
                self.srs,
                self.num_bands,
                self.pixel_type,
                self.product_definition,
                self.product_band_definitions,
            )
            return self.m_base._updateResponse(resp, status=True, output=mdPath)
        except Exception as e:
            self.log(f"Failed!\n{arcpy.GetMessages()}\n{e}", self.const_critical_text)
        return False

    def init(self, config):
        """init"""
        if not self.m_base.m_doc:
            self.log("\nMissing configuration file.", self.const_critical_text)
            return False
        node_list = self.m_base.m_doc.getElementsByTagName("MosaicDataset")
        if node_list.length == 0:
            self.log("\nMosaicDatasets node not found! Invalid schema.", self.const_critical_text)
            return False
        try:
            for node in node_list[0].childNodes:
                node = node.nextSibling
                if node is not None and node.nodeType == self.m_base.NODE_TYPE_ELEMENT:
                    if node.nodeName == "SRS":  # required arg
                        self.srs = node.firstChild.nodeValue
                    elif node.nodeName == "pixel_type":  # optional arg
                        if node.hasChildNodes():
                            self.pixel_type = node.firstChild.nodeValue
                    elif node.nodeName == "num_bands":  # optional arg
                        if node.hasChildNodes():
                            self.num_bands = node.firstChild.nodeValue
                    elif node.nodeName == "product_definition":  # optional arg
                        if node.hasChildNodes():
                            self.product_definition = node.firstChild.nodeValue
                    elif node.nodeName == "product_band_definitions":  # optional arg
                        if node.hasChildNodes():
                            self.product_band_definitions = node.firstChild.nodeValue
        except BaseException:
            self.log("\nErr. Reading MosaicDataset nodes.", self.const_critical_text)
            return False
        return True
