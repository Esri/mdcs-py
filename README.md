# mdcs-py

The Mosaic Dataset Configuration Script (MDCS) is a Python script that reads parameters stored in an xml file in order to create, configure, and populate a [mosaic dataset](http://desktop.arcgis.com/en/arcmap/10.3/manage-data/raster-and-images/what-is-a-mosaic-dataset.htm).

If you want to try out MDCS, review the documentation included in the repo for instructions, and download the suggested sample data from [ArcGIS Online](http://pm.maps.arcgis.com/home/item.html?id=5f6c9a157ffc45c4863996c2987f4ac9). 

This repo also contains [MDTools](https://github.com/Esri/mdcs-py/blob/master/Documentation/MDTools_ReadMe.pdf), a command line tool that simplifies some common management tasks when working with rasters in a mosaic dataset.

## Features

* Automate the creation of multiple mosaic datasets
* Configure multiple mosaic datasets using XML files
* Built-in verbose reporting and logging system
* Command line usage via batch files 
* Compatible with ArcMap 10.1+ and ArcGIS Pro 1.0+ (MDTools requires ArcMap 10.6.1+ or ArcGIS Pro 2.2+)
* Use MDTools to do the following: 
	- Embed raster proxies in a mosaic dataset
	- Perform search and replace for embedded raster proxy strings
	- Export file locations to a text file for rasters in a mosaic dataset in a given area of interest (AOI) and with a specific cell size

## Instructions

1. Download the ZIP file (called mdcs-py-master.zip)
2. Create a folder called Image_Mgmt_Workflows in the root of your C: drive
3. Unzip the contents of the MDCS ZIP file into the Image_Mgmt_Workflows folder

To get started with MDTools:

4. Navigate to C:/Image_Mgmt_Workflows/mdcs-py/MDTools_Setup.zip
5. Unzip the contents, then double-click MDTools_Setup.exe to install the tools.
6. Refer to the [MDTools documentation](https://github.com/Esri/mdcs-py/blob/master/Documentation/MDTools_ReadMe.pdf) to get started.

## Suggested Requirements

* Notepad / XML Editor
* Knowledge of [Mosaic Datasets](https://pro.arcgis.com/en/pro-app/help/data/imagery/mosaic-datasets.htm)
* Knowledge of Python

## Resources

* Dowload [sample data](http://pm.maps.arcgis.com/home/item.html?id=5f6c9a157ffc45c4863996c2987f4ac9) for use with MDCS.
* See the [Managing Elevation workflow scripts](http://www.arcgis.com/home/item.html?id=d2a055e12af14258a931fdc3ecf2c8b4) on ArcGIS Online for an example application of MDCS.

## Issues

Find a bug or want to request a new feature?  Please let us know by submitting an issue.

## Contributing

Anyone and everyone is welcome to contribute. 

## Licensing
Copyright 2012 Esri

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

A copy of the license is available in the repository's [license.txt](https://github.com/ArcGIS/mdcs-py/blob/master/license.txt) file.



