#-------------------------------------------------------------------------------
# Name  	    	: MDCS.py
# ArcGIS Version	: ArcGIS 10.1 sp1
# Script Version	: 20130801
# Name of Company 	: Environmental System Research Institute
# Author        	: ESRI raster solution team
# Purpose 	    	: This is the main program entry point to MDCS.
# Created	    	: 14-08-2012
# LastUpdated  		: 16-09-2013
# Required Argument : -i:<config_file>
# Optional Argument : -c|-m|-s|-l
# Usage         : python.exe MDCS.py -c:<Optional:command(s)> -i:<config_file>
# Type 'python.exe mdcs.py' to display the usage and a list of valid commands.
# Copyright	    : (c) ESRI 2012
# License	    : <your license>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

import arcpy
import sys, os

solutionLib_path = os.path.dirname(__file__)        #set the location to the solutionsLib path
sys.path.append(solutionLib_path)

sys.path.append(os.path.join(solutionLib_path, 'solutionsLog'))
import logger
import solutionsLib     #import Raster Solutions library
import Base


randomCount = 0

def postAddData(gdbPath, mdName, info):
    global randomCount

    mdName = info['md']
    obvalue = info['pre_AddRasters_record_count']
    fullPath = os.path.join(gdbPath, mdName)

    mosaicMDType = info['type'].lower()

    if(mosaicMDType == 'source'):
        lyrName = "Mosaiclayer" + str(randomCount)
        randomCount += 1
        expression = "OBJECTID >" + str(obvalue)

        try:
            arcpy.MakeMosaicLayer_management(fullPath,lyrName,expression)
        except:
            log.Message("Failed to make mosaic layer (%s)" % (lyrName), log.const_critical_text)
            log.Message(arcpy.GetMessages(), log.const_critical_text)

            return False

        try:
            fieldName = 'dataset_id'
            fieldExist = arcpy.ListFields(fullPath, fieldName)
            if len(fieldExist) == 0:
                arcpy.AddField_management(fullPath, fieldName, "TEXT", "", "", "50")
            log.Message("Calculating \'Dataset ID\' for the mosaic dataset (%s) with value (%s)" % (mdName, info['Dataset_ID']), log.const_general_text)
            arcpy.CalculateField_management(lyrName, fieldName, "\"" + info['Dataset_ID'] + "\"", "PYTHON")
        except :
            log.Message('Failed to calculate \'Dataset_ID\'', log.const_critical_text)
            log.Message(arcpy.GetMessages(), log.const_critical_text)

            return False

        try:
            arcpy.Delete_management(lyrName)
        except:
            log.Message("Failed to delete the layer", log.const_critical_text)
            log.Message(arcpy.GetMessages(), log.const_critical_text)

            return False

    return True

def main(argc, argv):

    argc = len(argv)
    if (argc < 2):

    #command-line argument codes.
    #-i:config file.
    #-c:command codes
    #-m:mosaic dataset name
    #-s:Source data paths. (as inputs to command (AR/AR)
    #-l:Full path to log file (including file name)

        user_args = \
        [
        "-m: Mosaic dataset path including GDB and MD name [e.g. c:\WorldElevation.gdb\Portland]",
        "-s: Source data paths. (As inputs to command (AR)",
        "-l: Log file output path [path+file name]",
        "-artdem: Update DEM path in ART file"
        ]

        print "\nMDCS.py v5.6 [20130801]\nUsage: MDCS.py -c:<Optional:command> -i:<config_file>" \
        "\n\nFlags to override configuration values," \

        for arg in user_args:
            print arg

        print \
        "\nNote: Commands can be combined with '+' to do multiple operations." \
        "\nAvailable commands:"

        user_cmds = solutionsLib.Solutions().getAvailableCommands()
        for key in user_cmds:
            print "\t" + key + ' = ' + user_cmds[key]['desc']

        sys.exit(1)


    base = Base.Base()
    global log
    log = logger.Logger();
    base.setLog(log)


    argIndx = 1
    md_path_ = artdem = config = com = log_folder = ''

    while(argIndx < argc):
        (values) = argv[argIndx].split(':')
        if (len(values[0]) < 2 or
            values[0][:1] != '-' and
            values[0][:1] != '#'):
            argIndx += 1
            continue

        exSubCode = values[0][1:len(values[0])].lower()
        subCode = values.pop(0)[1].lower()

        value = ':'.join(values).strip()

        if (subCode == 'c'):
            com = value.replace(' ', '')        #remove spaces in between.
        elif(subCode == 'i'):
            config = value
        elif(subCode == 'm'):
            md_path_ = value
        elif(subCode == 's'):
            base.m_sources = value
        elif(subCode == 'l'):
            log_folder =  value
        elif(exSubCode == 'artdem'):
            artdem =  value
        elif(subCode == 'p'):
            aryP = value.split('$')
            pMax = len(aryP) - 1
            if (pMax == 0):
                argIndx += 1
                continue

            dynamic_var = aryP[pMax].upper()

            del aryP[pMax]
            v = ''.join(aryP)
            if (dynamic_var.strip() != ''):
                if (base.m_dynamic_params.has_key(dynamic_var) == False):
                    base.m_dynamic_params[dynamic_var] = v

        argIndx += 1


    if (md_path_ != ''):
        (p, f) = os.path.split(md_path_)
        f = f.strip()
        const_gdb_ext_len_ = len(base.const_geodatabase_ext)
        ext = p[-const_gdb_ext_len_:].lower()
        if ((ext == base.const_geodatabase_ext.lower() or
            ext == base.const_geodatabase_SDE_ext.lower()) and
            f != ''):
            p = p.replace('\\', '/')
            w = p.split('/')
            workspace_ = ''
            for i in range(0, len(w) - 1):
                workspace_ += w[i] + '/'

            gdb_ = w[len(w) -1]
            base.m_workspace = workspace_
            base.m_geodatabase = w[len(w) - 1]
            base.m_mdName = f


    if (os.path.isfile(config) == False):
        errMessage = u"Error: Input config file is not specified/not found! " + config
        arcpy.AddMessage(errMessage)
        return False


    if (artdem != ''):
        (base.m_art_ws, base.m_art_ds) = os.path.split(artdem)
        base.m_art_apply_changes = True


    comInfo = {
    'AR' : { 'cb' : postAddData }       #assign a callback function to run custom user code when adding rasters.
    }


    configName, ext = os.path.splitext(config)
    configName = os.path.basename(configName)



    if (com == ''):
        com = base.const_cmd_default_text

    if (argv[1].lower() == '#gprun'):
        log.isGPRun = True
    log.Project ('MDCS')
    log.LogNamePrefix(configName)
    log.StartLog()

    log_output_folder  = os.path.join(os.path.dirname(solutionLib_path), 'logs')

    if (log_folder != ''):
        (path, fileName) = os.path.split(log_folder)
        if (path != ''):
            log_output_folder = path
        if (fileName != ''):
            log.LogFileName(fileName)

    log.SetLogFolder(log_output_folder)
    solutions = solutionsLib.Solutions(base)
    success = solutions.run(config, com, comInfo)

    log.WriteLog('#all')   #persist information/errors collected.

    print "Done..."

if __name__ == '__main__':
    main(3, sys.argv)


