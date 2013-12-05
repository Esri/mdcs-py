#-------------------------------------------------------------------------------
# Name  	    	: MDCS_UC.py
# ArcGIS Version	: ArcGIS 10.1 sp1
# Script Version	: 20131205
# Name of Company 	: Environmental System Research Institute
# Author        	: ESRI raster solution team
# Purpose 	    	: A class to define all user defined functions to extend
# the built in functions/commnands chain
# Created	    	: 20131017
# LastUpdated  		: 20131023
# Required Argument 	: Not applicable
# Optional Argument 	: Not applicable
# Usage         	:  To be called only internally by 'MDCS' code.
# Copyright	    	: (c) ESRI 2013
# License	    	: <your license>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

import os
import sys
import arcpy

class UserCode:
    def sample00(self, data):

        workspace = data['workspace']
        md = data['mosaicdataset']

        log = data['log']
        log.Message('%s\\%s' % (workspace, md), 0)

        return True



    def sample01(self, data):

        log = data['log']
        log.Message('hello world', 0)

        return True


    def customCV(self, data):

        workspace = data['workspace']
        md = data['mosaicdataset']

        ds = os.path.join(workspace, md)
        ds_cursor = arcpy.UpdateCursor(ds)
        if (ds_cursor != None):
            print 'Calculating values..'
            row = ds_cursor.next()
            while(row != None):
                row.setValue('MinPS', 0)
                row.setValue('MaxPS', 300)

                WRS_Path = row.getValue('WRS_Path')
                WRS_Row = row.getValue('WRS_Row')

                if (WRS_Path != None and
                    WRS_Row != None):
                    PR = (WRS_Path*1000)+WRS_Row
                    row.setValue('PR', PR)


                AcquisitionData = row.getValue('AcquisitionDate')
                if (AcquisitionData != None):
                    AcquisitionData = str(AcquisitionData).replace('-', '/')
                    day = int(AcquisitionData.split()[0].split('/')[1])
                    row.setValue('Month', day)


                grp_name = row.getValue('GroupName')
                if (grp_name != None):
                    CMAX_INDEX = 16
                    if (len(grp_name) >= CMAX_INDEX):
                        row.setValue('DayOfYear', int(grp_name[13:CMAX_INDEX]))
                        row.setValue('Name', grp_name.split('_')[0] + '_' + row.getValue('Tag'))

                ds_cursor.updateRow(row)
                row = ds_cursor.next()

            del ds_cursor


        return True
