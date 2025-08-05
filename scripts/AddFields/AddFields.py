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
# Name:  AddFields.py
# Description:  Creates custom fields in mosaic datasets.
# Version:  20250310
# Requirements:  ArcGIS 10.1 SP1
# Optional Arguments: <optional args if any>
# Usage: AddFields.py [arguments]
# Author:  Esri Imagery Workflows team
# -------------------------------------------------------------------------------
#!/usr/bin/env python

import arcpy
import os
import sys
from defusedxml import minidom
from Base.Base import Base as CBase


class AddFields(CBase):

    def __init__(self, base):
        self.fieldNameList = []
        self.fieldTypeList = []
        self.fieldLengthList = []

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
                fieldExist = arcpy.ListFields(mdPath, self.fieldNameList[j])
                if len(fieldExist) == 0:
                    arcpy.AddField_management(mdPath, self.fieldNameList[j], self.fieldTypeList[j], "", "", self.fieldLengthList[j])
        except BaseException:
            self.log("Error: " + arcpy.GetMessages(), self.const_critical_text)
            return False

        return True

    def init(self, config):

        Nodelist = self.m_base.m_doc.getElementsByTagName("MosaicDataset")
        if Nodelist.length == 0:
            self.log("\nError: MosaicDataset node not found! Invalid schema.", self.const_critical_text)
            return False

        try:
            for node in Nodelist[0].childNodes:
                node = node.nextSibling
                if node is not None and node.nodeType == self.m_base.NODE_TYPE_ELEMENT:
                    if node.nodeName == "Name":
                        try:
                            if self.m_base.m_mdName == "":
                                self.m_base.m_mdName = node.firstChild.nodeValue
                            break
                        except BaseException:
                            Error = True
        except BaseException:
            self.log("\nError: reading MosaicDataset nodes.", self.const_critical_text)
            return False

        Nodelist = self.m_base.m_doc.getElementsByTagName("Fields")
        if Nodelist.length == 0:
            self.log("Error: Fields node not found! Invalid schema.", self.const_critical_text)
            return False

        try:
            for node in Nodelist[0].childNodes:
                if node.nodeType == self.m_base.NODE_TYPE_ELEMENT:
                    for n in node.childNodes:
                        if n.nodeType == self.m_base.NODE_TYPE_ELEMENT:
                            nodeName = n.nodeName.upper()
                            if nodeName == "NAME":
                                self.fieldNameList.append(n.firstChild.nodeValue)
                            elif nodeName == "TYPE":
                                self.fieldTypeList.append(n.firstChild.nodeValue)
                            elif nodeName == "LENGTH":
                                try:
                                    self.fieldLengthList.append(n.firstChild.nodeValue)
                                except BaseException:
                                    self.fieldLengthList.append("")
        except BaseException:
            self.log("\nError: Reading fields information!", self.const_critical_text)
            return False

        fields_len = len(self.fieldNameList)
        if len(self.fieldTypeList) != fields_len or len(self.fieldLengthList) != fields_len:
            self.log("\nError: Number of Field(Name, Type, Len) do not match!", self.const_critical_text)
            return False

        return True
