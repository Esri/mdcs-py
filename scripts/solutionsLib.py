#-------------------------------------------------------------------------------
# Name  	    	: SolutionsLib
# ArcGIS Version	: ArcGIS 10.1 sp1
# Script Version	: 20130225
# Name of Company 	: Environmental System Research Institute
# Author        	: ESRI raster solution team
# Date          	: 16-09-2012
# Purpose 	    	: To have a library of python modules to facilitate code to reuse for Raster Solutions projects.
# Created	    	: 14-08-2012
# LastUpdated  		: 06-03-2013
# Required Argument 	: Not applicable
# Optional Argument 	: Not applicable
# Usage         	:  Object of this class should be instantiated.
# Copyright	    	: (c) ESRI 2012
# License	    	: <your license>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

import arcpy
import sys, os
from xml.dom import minidom


scriptPath = os.path.dirname(__file__)
sys.path.append(os.path.join(scriptPath, 'Base'))

import Base


class Solutions(Base.Base):

    processInfo = None
    userInfo = None
    config = ''
    m_base = None

    def __init__(self, base=None):
        if (base != None):
            self.setLog(base.m_log)
        self.m_base = base

        self.processInfo = None
        self.userInfo = None
        self.config = ''


    def getAvailableCommands(self):
        return self.commands

    #mapping commands to functions
    def executeCommand(self, com):

    #create the geodatabse to hold all relevant mosaic datasets.
        if (com == 'CM'):
            createMD = self.CreateMD.CreateMD(self.m_base)
            bSuccess = createMD.init(self.config)
            if (bSuccess):
                bSuccess = createMD.createGeodataBase()
                return createMD.createMD()
            return False

    #Add custom fields to elevation mosaic datasets.
        elif (com == 'AF'):
            addFields = self.AddFields.AddFields(self.m_base)
            bSuccess = addFields.init(self.config)
            if (bSuccess):
                return addFields.CreateFields()
            return False

    #Add rasters/data to mosaic datasets.
        elif (com == 'AR'):
            addRasters = self.AddRasters.AddRasters(self.m_base)
            bSuccess = addRasters.init(self.config)
            if (bSuccess):
                if (self.userInfo.has_key(com)):
                    if (self.userInfo[com].has_key('cb')):
                        bSuccess = addRasters.AddCallBack(self.userInfo[com]['cb'])
                return addRasters.AddRasters()
            return False

    #Create referenced mosaic datasets.
        elif(com == 'CR'):
            createRefMD = self.CreateRefMD.CreateReferencedMD(self.m_base)
            bSuccess = createRefMD.init(self.config)
            if (bSuccess):
                return createRefMD.createReferencedMD()
            return False

        elif(com == 'SP'):
            setProps = self.SetMDProperties.SetMDProperties(self.m_base)
            bSuccess = setProps.init(self.config)
            if (bSuccess):
                path = os.path.join(setProps.gdbPath, setProps.mosaicDataset)
                return setProps.setMDProperties(path)
            return False

        elif (com == 'CBMD'):
            try:
                self.m_log.Message("\tColor Balancing mosaic dataset : " + self.processInfo.mdName, self.m_log.const_general_text)
                fullPath = os.path.join(self.processInfo.geoPath, self.processInfo.mdName)
                processKey = 'colorbalancemosaicdataset'
                arcpy.ColorBalanceMosaicDataset_management(fullPath,
                self.getProcessInfoValue(processKey,'balancing_method'),
                self.getProcessInfoValue(processKey,'color_surface_type'),
                self.getProcessInfoValue(processKey,'target_raster'),
                self.getProcessInfoValue(processKey,'gamma'),
                self.getProcessInfoValue(processKey,'exclude_raster'),
                self.getProcessInfoValue(processKey,'stretch_type'),
                self.getProcessInfoValue(processKey,'block_field')
                )
                return True
            except:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False

        elif (com == 'ERF'):
            try:
                self.m_log.Message("\tEditing Raster function : " + self.processInfo.mdName, self.m_log.const_general_text)
                fullPath = os.path.join(self.processInfo.geoPath, self.processInfo.mdName)
                processKey = 'editrasterfunction'
                arcpy.EditRasterFunction_management(fullPath,
                self.getProcessInfoValue(processKey,'edit_mosaic_dataset_item'),
                self.getProcessInfoValue(processKey,'edit_options'),
                self.getProcessInfoValue(processKey,'function_chain_definition'),
                self.getProcessInfoValue(processKey,'location_function_name'),
                )
                return True
            except:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False

        elif (com == 'CS'):
            try:
                self.m_log.Message("\tCalculate statistic for the mosaic dataset : " + self.processInfo.mdName, self.m_log.const_general_text)
                fullPath = os.path.join(self.processInfo.geoPath, self.processInfo.mdName)
                processKey = 'calculatestatistics'
                arcpy.CalculateStatistics_management(fullPath,
                self.getProcessInfoValue(processKey,'x_skip_factor'),
                self.getProcessInfoValue(processKey,'y_skip_factor'),
                self.getProcessInfoValue(processKey,'ignore_values'),
                self.getProcessInfoValue(processKey,'skip_existing'),
                self.getProcessInfoValue(processKey,'area_of_interest')
                )
                return True
            except:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False

        elif (com == 'BPS'):
            try:
                self.m_log.Message("\tRecomputing footprint for the mosaic dataset : " + self.processInfo.mdName, self.m_log.const_general_text)
                fullPath = os.path.join(self.processInfo.geoPath, self.processInfo.mdName)
                processKey = 'buildpyramidsandstatistics'
                arcpy.BuildPyramidsAndStatistics_management(fullPath,
                self.getProcessInfoValue(processKey,'include_subdirectories'),
                self.getProcessInfoValue(processKey,'build_pyramids'),
                self.getProcessInfoValue(processKey,'calculate_statistics'),
                self.getProcessInfoValue(processKey,'BUILD_ON_SOURCE'),
                self.getProcessInfoValue(processKey,'block_field'),
                self.getProcessInfoValue(processKey,'estimate_statistics'),
                self.getProcessInfoValue(processKey,'x_skip_factor'),
                self.getProcessInfoValue(processKey,'y_skip_factor'),
                self.getProcessInfoValue(processKey,'ignore_values'),
                self.getProcessInfoValue(processKey,'pyramid_level'),
                self.getProcessInfoValue(processKey,'SKIP_FIRST'),
                self.getProcessInfoValue(processKey,'resample_technique'),
                self.getProcessInfoValue(processKey,'compression_type'),
                self.getProcessInfoValue(processKey,'compression_quality'),
                self.getProcessInfoValue(processKey,'skip_existing')
                )
                return True
            except:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False

        elif(com == 'BP'):
            try:
                self.m_log.Message("\tBuilding Pyramid for the mosaic dataset/raster dataset : " + self.processInfo.mdName, self.m_log.const_general_text)
                fullPath = os.path.join(self.processInfo.geoPath, self.processInfo.mdName)
                processKey = 'buildpyramids'
                arcpy.BuildPyramids_management(fullPath,
                self.getProcessInfoValue(processKey,'pyramid_level'),
                self.getProcessInfoValue(processKey,'SKIP_FIRST'),
                self.getProcessInfoValue(processKey,'resample_technique'),
                self.getProcessInfoValue(processKey,'compression_type'),
                self.getProcessInfoValue(processKey,'compression_quality'),
                self.getProcessInfoValue(processKey,'skip_existing'))
                return True
            except:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False

        elif(com == 'BF'):
          try:
                self.m_log.Message("\tRecomputing footprint for the mosaic dataset : " + self.processInfo.mdName, self.m_log.const_general_text)
                fullPath = os.path.join(self.processInfo.geoPath, self.processInfo.mdName)

                processKey = 'buildfootprint'
                arcpy.BuildFootprints_management(
                fullPath,
                self.getProcessInfoValue(processKey, 'where_clause'),
                self.getProcessInfoValue(processKey, 'reset_footprint'),
                self.getProcessInfoValue(processKey, 'min_data_value'),
                self.getProcessInfoValue(processKey, 'max_data_value'),
                self.getProcessInfoValue(processKey, 'approx_num_vertices'),
                self.getProcessInfoValue(processKey, 'shrink_distance'),
                self.getProcessInfoValue(processKey, 'maintain_edges'),
                self.getProcessInfoValue(processKey, 'skip_derived_images'),
                self.getProcessInfoValue(processKey, 'update_boundary'),
                self.getProcessInfoValue(processKey, 'request_size'),
                self.getProcessInfoValue(processKey, 'min_region_size'),
                self.getProcessInfoValue(processKey, 'simplification_method')
                )

                return True
          except:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False

        elif (com == 'BS'):
            try:
                self.m_log.Message("\tBuild Seamline for the mosaic dataset : " + self.processInfo.mdName, self.m_log.const_general_text)
                fullPath = os.path.join(self.processInfo.geoPath, self.processInfo.mdName)
                processKey = 'buildseamlines'
                arcpy.BuildSeamlines_management(fullPath,
                self.getProcessInfoValue(processKey,'cell_size'),
                self.getProcessInfoValue(processKey,'sort_method'),
                self.getProcessInfoValue(processKey,'sort_order'),
                self.getProcessInfoValue(processKey,'order_by_attribute'),
                self.getProcessInfoValue(processKey,'order_by_base_value'),
                self.getProcessInfoValue(processKey,'view_point'),
                self.getProcessInfoValue(processKey,'computation_method'),
                self.getProcessInfoValue(processKey,'blend_width'),
                self.getProcessInfoValue(processKey,'blend_type'),
                self.getProcessInfoValue(processKey,'request_size'),
                self.getProcessInfoValue(processKey,'request_size_type')
                )
                return True
            except:
                self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                return False


        elif(com == 'DN'):
                fullPath = os.path.join(self.processInfo.geoPath, self.processInfo.mdName)
                try:
                    processKey = 'definemosaicdatasetnodata'
                    arcpy.DefineMosaicDatasetNoData_management(
                    fullPath,
                    self.getProcessInfoValue(processKey, 'num_bands'),
                    self.getProcessInfoValue(processKey, 'bands_for_nodata_value'),
                    self.getProcessInfoValue(processKey, 'bands_for_valid_data_range'),
                    self.getProcessInfoValue(processKey, 'where_clause'),
                    self.getProcessInfoValue(processKey, 'composite_nodata_value')
                    )
                    return True

                except:
                    self.log(arcpy.GetMessages(), self.m_log.const_critical_text)

        elif(com == 'IG'):
                fullPath = os.path.join(self.processInfo.geoPath, self.processInfo.mdName)
                try:
                    processKey = 'importgeometry'
                    importPath = self.getProcessInfoValue(processKey, 'input_featureclass')
                    const_ig_search_ = '.gdb\\'
                    igIndx = importPath.lower().find(const_ig_search_)
                    igIndxSep = importPath.find('\\')

                    if (igIndxSep == igIndx + len(const_ig_search_) - 1):
                        importPath = self.prefixFolderPath(importPath, self.const_import_geometry_features_path_)

                    arcpy.ImportMosaicDatasetGeometry_management(
                    fullPath,
                    self.getProcessInfoValue(processKey, 'target_featureclass_type'),
                    self.getProcessInfoValue(processKey, 'target_join_field'),
                    importPath,
                    self.getProcessInfoValue(processKey, 'input_join_field')
                    )
                    return True
                except:
                    self.log(arcpy.GetMessages(), self.m_log.const_critical_text)

        elif(com == 'IF'):
                fullPath = os.path.join(self.processInfo.geoPath, self.processInfo.mdName)
                processKey = 'importfieldvalues'

    # Step (11) : for the all the Dervied Mosaic Dataset importing the fields from the Attribute Lookup Table
                try:
                    j = 0
                    joinTable = self.getProcessInfoValue(processKey, 'input_featureclass')
                    confTableName = os.path.basename(joinTable)

                    joinFeildList = [f.name for f in arcpy.ListFields(joinTable)]
                    self.log(joinFeildList)
                    mlayer = os.path.basename(fullPath) +"layer" + str(j)
                    j = j + 1
                    arcpy.MakeMosaicLayer_management(fullPath,mlayer)
                    self.log("Joining the mosaic dataset layer with the configuration table", self.m_log.const_general_text)
                    mlayerJoin = arcpy.AddJoin_management(
                    mlayer + "/Footprint",
                    self.getProcessInfoValue(processKey, 'input_join_field'),
                    joinTable,
                    self.getProcessInfoValue(processKey, 'target_join_field'),
                    "KEEP_ALL"
                    )
                    for jfl in joinFeildList:
                        if jfl == "Comments" or jfl == "OBJECTID" or jfl == "Dataset_ID":
                            self.log("\t\tvalues exist for the field : " + jfl, self.m_log.const_general_text)
                        else:
                            fieldcal ="AMD_" + mdName + "_CAT." + jfl
                            fromfield = "["+confTableName+"." + jfl + "]"
                            try:
                                arcpy.CalculateField_management(mlayerJoin,fieldcal,fromfield)
                                self.log("\t\tDone calculating values for the Field :" + fieldcal, self.m_log.const_general_text)
                            except:
                                self.log("Failed to calculate values for the field : " + fieldcal, self.m_log.const_warning_text)
                                self.log(arcpy.GetMessages(), self.m_log.const_warning_text)
                    return True
                except:
                    self.log(arcpy.GetMessages(), self.m_log.const_critical_text)


        elif(com == 'BB'):
                fullPath = os.path.join(self.processInfo.geoPath, self.processInfo.mdName)
                processKey = 'buildboundary'
                self.log ("Building the boundary "+ self.getProcessInfoValue(processKey, 'simplification_method'))
                try:
                    arcpy.BuildBoundary_management(
                    fullPath,
                    self.getProcessInfoValue(processKey, 'where_clause'),
                    self.getProcessInfoValue(processKey, 'append_to_existing'),
                    self.getProcessInfoValue(processKey, 'simplification_method')
                    )
                    return True
                except:
                    self.log(arcpy.GetMessages(), self.m_log.const_critical_text)


        elif(com == 'SS'):
                fullPath = os.path.join(self.processInfo.geoPath, self.processInfo.mdName)
                processKey = 'setstatistics'
                self.log("Setting MD statistics for:" + fullPath, self.m_log.const_general_text)
                stats_file_ss = self.getProcessInfoValue(processKey, 'stats_file')
                if stats_file_ss != '#' and stats_file_ss != '' :
                    stats_file_ss = self.prefixFolderPath(self.getProcessInfoValue(processKey, 'stats_file'), self.const_statistics_path_)

                try:
                    arcpy.SetRasterProperties_management(
                    fullPath,
                    self.getProcessInfoValue(processKey, 'data_type'),
                    self.getProcessInfoValue(processKey, 'statistics'),
                    stats_file_ss,
                    self.getProcessInfoValue(processKey, 'nodata')
                     )
                    return True
                except:
                    self.log(arcpy.GetMessages(), self.m_log.const_critical_text)

        elif(com == 'CC'):
                fullPath = os.path.join(self.processInfo.geoPath, self.processInfo.mdName)
                processKey = 'calculatecellsizeranges'
                self.log("Calculating cell ranges for:" + fullPath, self.m_log.const_general_text)

                try:
                    arcpy.CalculateCellSizeRanges_management(
                    fullPath,
                    self.getProcessInfoValue(processKey, 'where_clause'),
                    self.getProcessInfoValue(processKey, 'do_compute_min'),
                    self.getProcessInfoValue(processKey, 'do_compute_max'),
                    self.getProcessInfoValue(processKey, 'max_range_factor'),
                    self.getProcessInfoValue(processKey, 'cell_size_tolerance_factor'),
                    self.getProcessInfoValue(processKey, 'update_missing_only'),
                     )
                    return True
                except:
                    self.log(arcpy.GetMessages(), self.m_log.const_critical_text)

        elif(com == 'BO'):
                fullPath = os.path.join(self.processInfo.geoPath, self.processInfo.mdName)
                processKey = 'buildoverviews'
                self.log("Building overviews for:" + fullPath, self.m_log.const_general_text)

                try:
                    arcpy.BuildOverviews_management(
                    fullPath,
                    self.getProcessInfoValue(processKey, 'where_clause'),
                    self.getProcessInfoValue(processKey, 'define_missing_tiles'),
                    self.getProcessInfoValue(processKey, 'generate_overviews'),
                    self.getProcessInfoValue(processKey, 'generate_missing_images'),
                    self.getProcessInfoValue(processKey, 'regenerate_stale_images')
                     )
                    return True
                except:
                    self.log(arcpy.GetMessages(), self.m_log.const_critical_text)

        elif(com == 'DO'):
                fullPath = os.path.join(self.processInfo.geoPath, self.processInfo.mdName)
                processKey = 'defineoverviews'
                self.log("Define overviews for:" + fullPath, self.m_log.const_general_text)

                try:
                    arcpy.DefineOverviews_management(
                    fullPath,
                    self.getProcessInfoValue(processKey, 'overview_image_folder'),
                    self.getProcessInfoValue(processKey, 'in_template_dataset'),
                    self.getProcessInfoValue(processKey, 'extent'),
                    self.getProcessInfoValue(processKey, 'pixel_size'),
                    self.getProcessInfoValue(processKey, 'number_of_levels'),
                    self.getProcessInfoValue(processKey, 'tile_rows'),
                    self.getProcessInfoValue(processKey, 'tile_cols'),
                    self.getProcessInfoValue(processKey, 'overview_factor'),
                    self.getProcessInfoValue(processKey, 'force_overview_tiles'),
                    self.getProcessInfoValue(processKey, 'resampling_method'),
                    self.getProcessInfoValue(processKey, 'compression_method'),
                    self.getProcessInfoValue(processKey, 'compression_quality')
                     )
                    return True
                except:
                    self.log(arcpy.GetMessages(), self.m_log.const_critical_text)

        elif(com == 'AI'):
                fullPath = os.path.join(self.processInfo.geoPath, self.processInfo.mdName)
                processKey = 'addindex'
                self.log("Adding Index:" + fullPath, self.m_log.const_general_text)

                maxValues = len(self.processInfo.processInfo[processKey])
                isError = False
                for indx in range(0, maxValues):

                    try:
                        arcpy.AddIndex_management(fullPath,
                        self.getProcessInfoValue(processKey, 'fields', indx),
                        self.getProcessInfoValue(processKey, 'index_name', indx),
                        self.getProcessInfoValue(processKey, 'unique', indx),
                        self.getProcessInfoValue(processKey, 'ascending', indx)
                        )
                    except:
                        self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                        isError = True

                return not isError


        elif(com == 'CV'):
                    fullPath = os.path.join(self.processInfo.geoPath, self.processInfo.mdName)
                    processKey = 'calculatevalues'
                    maxValues = len(self.processInfo.processInfo[processKey])

                    self.log("Calculate values:" + fullPath, self.m_log.const_general_text)
                    isError = False

                    for indx in range(0, maxValues):
                        layername = fullPath
                        if not self.getProcessInfoValue(processKey, 'query', indx) == '#':
                            layername = self.processInfo.mdName + "_layer"
                            arcpy.MakeMosaicLayer_management(fullPath,layername, self.getProcessInfoValue(processKey,'query', indx))
                        try:
                            arcpy.CalculateField_management(layername,
                            self.getProcessInfoValue(processKey, 'fieldname', indx),
                            self.getProcessInfoValue(processKey, 'expression', indx),
                            self.getProcessInfoValue(processKey, 'expression_type', indx),
                            self.getProcessInfoValue(processKey, 'code_block', indx)
                            )
                        except:
                            self.log(arcpy.GetMessages(), self.m_log.const_critical_text)
                            isError = True
                        try:
                            if (layername != fullPath):
                                arcpy.Delete_management(layername)
                        except:
                            log.Message(arcpy.GetMessages(), log.const_warning_text)
                            isError = True

                    return not isError

        elif(com == 'CP'):
                self.log("Compacting file geodatabase:" + self.processInfo.geoPath, self.m_log.const_general_text)

                try:
                    arcpy.Compact_management(self.processInfo.geoPath)
                    return True
                except:
                    self.log(arcpy.GetMessages(), self.m_log.const_critical_text)


        elif(com == 'SY'):
                fullPath = os.path.join(self.processInfo.geoPath, self.processInfo.mdName)
                processKey = 'synchronizemosaicdataset'
                self.log("Synchronize mosaic dataset:" + fullPath, self.m_log.const_general_text)

                try:
                    arcpy.SynchronizeMosaicDataset_management(
                    fullPath,
                    self.getProcessInfoValue(processKey, 'where_clause'),
                    self.getProcessInfoValue(processKey, 'new_items'),
                    self.getProcessInfoValue(processKey, 'sync_only_stale'),
                    self.getProcessInfoValue(processKey, 'update_cellsize_ranges'),
                    self.getProcessInfoValue(processKey, 'update_boundary'),
                    self.getProcessInfoValue(processKey, 'update_overviews'),
                    self.getProcessInfoValue(processKey, 'build_pyramids'),
                    self.getProcessInfoValue(processKey, 'calculate_statistics'),
                    self.getProcessInfoValue(processKey, 'build_thumbnails'),
                    self.getProcessInfoValue(processKey, 'build_item_cache'),
                    self.getProcessInfoValue(processKey, 'rebuild_raster'),
                    self.getProcessInfoValue(processKey, 'update_fields'),
                    self.getProcessInfoValue(processKey, 'fields_to_update'),
                    self.getProcessInfoValue(processKey, 'existing_items'),
                    self.getProcessInfoValue(processKey, 'broken_items')
                     )
                    return True
                except:
                    self.log(arcpy.GetMessages(), self.m_log.const_critical_text)


        return False            #main function body return, no matching command found!



    commands = \
    {
    'CM' :
        {   'desc' : 'Create new mosaic dataset.',
            'fnc' : executeCommand
        },
    'CR' :
        {   'desc' : 'Create new referenced mosaic dataset.',
            'fnc' : executeCommand
        },
    'AF' :
        {   'desc' : 'Add fields.',
            'fnc' : executeCommand
        },
    'AR' :
        {   'desc' : 'Add rasters/data to a mosaic dataset.',
            'fnc' : executeCommand
        },
    'BF' :
        {   'desc' : 'Build footprint.',
            'fnc' : executeCommand
        },
    'BS' :
        {   'desc' : 'Build Seamlines.',
            'fnc' : executeCommand
        },
    'BP' :
        {   'desc' : 'Build Pyramid.',
            'fnc' : executeCommand
        },
    'CS' :
        {   'desc' : 'Calculate Statistic.',
            'fnc' : executeCommand
        },
    'CBMD' :
        {   'desc' : 'Color Balance Mosaic Dataset.',
            'fnc' : executeCommand
        },
    'BPS' :
        {   'desc' : 'Build Pyramid and Statistic.',
            'fnc' : executeCommand
        },
    'ERF' :
        {   'desc' : 'Edit Raster Function.',
            'fnc' : executeCommand
        },
    'DN' :
        {   'desc' : 'Define no data values.',
            'fnc' : executeCommand
        },
    'SP' :
        {   'desc' : 'Set mosaic dataset properties.',
            'fnc' : executeCommand
        },
    'IG' :
        {   'desc' : 'Import mosaic dataset geometry.',
            'fnc' : executeCommand
        },
    'IF' :
        {   'desc' : 'Import field values/calculate fields.',
            'fnc' : executeCommand
        },
    'BB' :
        {   'desc' : 'Build boundary.',
            'fnc' : executeCommand
        },
    'SS' :
        {   'desc' : 'Set statistics for a raster or mosaic dataset.',
            'fnc' : executeCommand
        },
    'CC' :
        {   'desc' : 'Computes the minimum and maximum cell sizes for the rasters in a mosaic dataset.',
            'fnc' : executeCommand
        },
    'BO' :
        {   'desc' : 'Defines and generates overviews for a mosaic dataset.',
            'fnc' : executeCommand
        },
    'DO' :
        {   'desc' : 'Defines the tiling schema and properties of the preprocessed raster datasets.',
            'fnc' : executeCommand
        },
    'AI' :
        {   'desc' : 'Adds attribute index on the Mosaic Dataset.',
            'fnc' : executeCommand
        },
    'CV' :
        {   'desc' : 'Calculate values on the Mosaic Dataset.',
            'fnc' : executeCommand
        },
    'CP' :
        {   'desc' : 'Compact file geodatabase.',
            'fnc' : executeCommand
        },
    'SY' :
        {   'desc' : 'Rebuilds or updates each raster item in the mosaic dataset.',
            'fnc' : executeCommand
        }
    }


    #mapping of config/component paths.

    base_path_ = scriptPath + '\\'

    com_locations = \
    {
    'CreateMD' :
        {
            'pyc' : base_path_ + 'CreateMD',
        },
    'AddFields' :
        {
            'pyc' : base_path_ + 'AddFields/',
        },
    'AddRasters' :
        {
            'pyc' : base_path_ + 'AddRasters/',
        },
    'SetMDProperties' :
        {
            'pyc' : base_path_ + 'SetMDProperties/',
        },
    'CreateRefMD' :
        {
            'pyc' : base_path_ + 'CreateRefMD/',
        },
    'ProcessInfo' :
        {
            'pyc' : base_path_ + 'ProcessInfo/',
        },
    'Base' :
        {
            'pyc' : base_path_ + 'Base/',
        }
    }


    #update environment path to include where components reside.
    sys.path.append(com_locations['CreateMD']['pyc'])
    sys.path.append(com_locations['AddFields']['pyc'])
    sys.path.append(com_locations['AddRasters']['pyc'])
    sys.path.append(com_locations['CreateRefMD']['pyc'])
    sys.path.append(com_locations['SetMDProperties']['pyc'])
    sys.path.append(com_locations['ProcessInfo']['pyc'])
    sys.path.append(com_locations['Base']['pyc'])


    #import all the modules required for the elevation project.
    #import Base
    import CreateMD
    import AddFields
    import AddRasters
    import SetMDProperties
    import CreateRefMD
    import ProcessInfo



    def getProcessInfoValue(self, process, key, index = -1):

        if (index > -1):
            if (self.processInfo.processInfo[process][index].has_key(key)):
                    return self.processInfo.processInfo[process][index][key]
            return '#'

        if (self.processInfo.processInfo[process].has_key(key)):
                return self.processInfo.processInfo[process][key]

        return '#'


    def run(self, conf, com, info):

        self.config = conf       #configuration/XML template
        self.userInfo = info     #callback information for commands /e.t.c.


        self.processInfo = self.ProcessInfo.ProcessInfo(self.m_base)
        bSuccess = self.processInfo.init(self.config)
        if (bSuccess == False):
            return False

        bSuccess = self.processInfo.hasProcessInfo

        #split commands with '+'
        self.log('Using template:' + self.config, self.const_general_text)

        com_ = com
        if (com_.upper() == self.const_cmd_default_text.upper()):
            try:
                doc = minidom.parse(self.config)
                com_ = self.getXMLNodeValue(doc, "Command")         #gets command defaults.
                self.log('Using default command(s):' + com_)

            except:
                self.log("Error: Reading input config file:" + self.config + "\nQuitting...",
                self.const_critical_text)
                return False

            doc = None          # no longer necessary.

            if (len(com_.strip()) == 0):
                self.log('Error: Empty command.',
                self.const_critical_text)
                return False

        self.log('Processing command(s):' + com_.upper(), self.const_general_text)

        aryCmds = com_.split('+')
        for cmd in aryCmds:
            cmd = cmd.upper()
            if (self.commands.has_key(cmd) == False):
                self.log("Command/Err: Unknown command:" + cmd, self.const_general_text)
                continue

            if (self.isLog() == True):
                 self.m_log.CreateCategory(cmd)

            self.log("Command:" + cmd + '->' + self.commands[cmd]['desc'], self.const_general_text)
            success = 'OK'
            if (self.commands[cmd]['fnc'](self, cmd) == False):
                success = 'Failed!'
            self.log(success, self.const_status_text)

            if (self.isLog() == True):
                self.m_log.CloseCategory()

        return True
