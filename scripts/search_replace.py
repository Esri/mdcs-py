#-------------------------------------------------------------------------------
# Name  	        : searchReplace.py
# ArcGIS Version	: ArcGIS 10.1 sp1
# Script Version	: 20130801
# Name of Company 	: Environmental System Research Institute
# Author        	: ESRI raster solution team
# Purpose 	    	: This script is to search
# Created	    	: 14-08-2012
# LastUpdated  		: 17-09-2012
# Required Argument 	: Not applicable
# Optional Argument 	: Not applicable
# Usage         :  To run within ArcMap/Model Builder.
# Copyright	    : (c) ESRI 2012
# License	    : <your license>
#-------------------------------------------------------------------------------

import os,sys
from fnmatch import fnmatch

def main():
    pass

if __name__ == '__main__':
    main()


if len(sys.argv) <> 5:
    print " number of inputs are invalid"
    print " <path to the folder> <search string> <replace string> <file extension filter>"
    sys.exit()
parent_folder_path= sys.argv[1]
search = sys.argv[2]
replace = sys.argv[3]
pattern = sys.argv[4]

for path, subdirs, files in os.walk(parent_folder_path):
    for name in files:
        if fnmatch(name, pattern):
            newfilePath = os.path.join(path, name)

            file = open(newfilePath, 'r')
            xml = file.read()
            file.close()

            try:

                print newfilePath
                print "String [%s] replaced with [%s]" % (search, replace)
                print "-------------------------------"

                l_indx_ = xml.lower().index(search.lower())
                while(l_indx_ >= 0):
                    left_ = xml[0:l_indx_]
                    right = xml[l_indx_ + len(search):len(xml)]
                    xml = left_ + replace + right
                    try:
                        l_indx_ = xml.lower().index(search.lower(), l_indx_ + 1)
                    except:
                        l_indx_ = -1

                file = open(newfilePath, 'w')
                file.write(str(xml))
                file.close()

            except:
                found = False

            xml = ''
            file = ''
print "Done"