# ------------------------------------------------------------------------------
# Copyright 2018 Esri
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
# ------------------------------------------------------------------------------
# Name: PublishImageService.pyt
# Description: GP Tool for publish, update, delete imagery services
# Version: 20190128
# Requirements:
# Author: Esri Imagery Workflows Team
# ------------------------------------------------------------------------------

import sys
import os
import json
import time
import urllib
import requests
import arcpy
scripts = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'scripts')
sys.path.append(scripts)
solutionlog = os.path.join(scripts,"SolutionsLog")
sys.path.append(solutionlog)
from imagery_service import ImageryServices
requests.packages.urllib3.disable_warnings()


def get_servers():
    try:
        credentials_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'Parameter', 'credentials')
        filenames = []
        for _, _, files in os.walk(credentials_folder):
            filenames.extend(files)
        servers = [os.path.splitext(file)[0] for file in filenames if os.path.splitext(file)[1].lower() == '.json']
        return servers
    except:
        return []

def get_server_config_path(server_config_name):
    return os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'Parameter', 'credentials', server_config_name+'.json')

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [PublishImageService]


class PublishImageService(object):

    actions = {
                  "create": "Create Image Service",
                  "update": "Update Image Service",
                  "delete": "Delete Image Service"
              }
    actions_list = list(actions.values())

    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Publish Image Service"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        global error_message
        error_message = None
        server = arcpy.Parameter(displayName="Server",
                                 name="server",
                                 datatype="GPString",
                                 parameterType="Required",
                                 direction="Input",
                                 enabled=True)
        action = arcpy.Parameter(displayName="Action",
                                 name="action",
                                 datatype="GPString",
                                 parameterType="Required",
                                 direction="Input",
                                 enabled=True)
        folder_name = arcpy.Parameter(displayName="Folder Name",
                                           name="folder_name",
                                           datatype="GPString",
                                           parameterType="Optional",
                                           direction="Input",
                                           enabled=True)
        service_name = arcpy.Parameter(displayName="Image Service Name",
                                       name="service_name",
                                       datatype="GPString",
                                       parameterType="Required",
                                       direction="Input",
                                       enabled=True)
        raster_url = arcpy.Parameter(displayName="Data path",
                                         name="raster_url",
                                         datatype=["DEMosaicDataset", "DEFile", "GPString"],
                                         parameterType="Required",
                                         direction="Input",
                                         enabled=True)
        instance_type = arcpy.Parameter(displayName="Instance Type",
                                        name="instance_type",
                                        datatype="GPString",
                                        parameterType="Required",
                                        direction="Input",
                                        enabled=True)
        description = arcpy.Parameter(displayName="Description",
                                      name="description",
                                      datatype="GPString",
                                      parameterType="Required",
                                      direction="Input",
                                      enabled=True)
        copyright = arcpy.Parameter(displayName="Copyright",
                                    name="copyright",
                                    datatype="GPString",
                                    parameterType="Optional",
                                    direction="Input",
                                    enabled=True)
        service_running_status = arcpy.Parameter(
                         displayName="Change service running status",
                         name="service_running_status",
                         datatype="GPString",
                         parameterType="Required",
                         direction="Input",
                         enabled=False)
        update_data_path = arcpy.Parameter(displayName="Data path",
                                           name="update_data_path",
                                           datatype=["DEMosaicDataset", "DEFile", "GPString"],
                                           parameterType="Optional",
                                           direction="Input",
                                           enabled=False)
        add_item_to_AGOL = arcpy.Parameter(
                         displayName="Add item to ArcGIS Online",
                         name="add_item_to_AGOL",
                         datatype='GPBoolean',
                         parameterType="Optional",
                         direction="Input",
                         enabled=True)
        add_item_to_AGOL.value=False
        instance_type.filter.list = ['Shared Instance', 'Dedicated Instance']
        instance_type.value = 'Dedicated Instance'
        action.filter.list = self.actions_list
        action.value = 'Create Image Service'
        params = [server, action, folder_name, service_name, raster_url,
                  instance_type, description, copyright,
                  service_running_status, update_data_path,
                  add_item_to_AGOL]
        return params

    def enableParams(self, enable_list, all_parameters):
        for param in all_parameters:
            if param in enable_list:
                param.enabled = True
                if 'String' in param.datatype and param.parameterType == 'Required':
                    if param.valueAsText == "None":
                        param.value = ""
            else:
                if 'String' in param.datatype and param.parameterType == 'Required':
                    if not param.value:
                        param.value = "None"
                param.enabled = False

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def mapParams(self, parameters_list):
        return {
                "server": parameters_list[0],
                "action": parameters_list[1],
                "folder_name": parameters_list[2],
                "service_name": parameters_list[3],
                "raster_url": parameters_list[4],
                "instance_type": parameters_list[5],
                "description": parameters_list[6],
                "copyright": parameters_list[7],
                "service_running_status": parameters_list[8],
                "update_data_path": parameters_list[9],
                "add_item_to_AGOL": parameters_list[10]
        }

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        global error_message
        error_message = ""
        params = self.mapParams(parameters)
        servers = get_servers()
        if not servers:
            error_message = "Please check if there is at least one server credentials file at Parameter/credentials folder."
            return
        if not params['server'].altered:
            params['server'].filter.list = servers
            params['server'].value = servers[0]
        imagery_service = ImageryServices(config_file=get_server_config_path(params['server'].valueAsText))
        get_folder_response = imagery_service.get_all_server_folders()
        if not get_folder_response.get('success'):
            error_message = 'Please check if the server credentials file has the correct image server url, username and password. Please restart Pro after entering the credentials'
            return
        if not params['folder_name'].altered:
            folders = get_folder_response['folders']
            folder_names = [folder.get('folderName') for folder in folders]
            params['folder_name'].value = ''
            params['folder_name'].filter.list = folder_names
        if params['server'].altered and not params['server'].hasBeenValidated:
            folders = get_folder_response['folders']
            folder_names = [folder.get('folderName') for folder in folders]
            params['folder_name'].value = ''
            params['folder_name'].filter.list = folder_names
        data_type = self.get_data_type(params['raster_url'].value)
        if data_type == 'md':
            if  not  params['instance_type'].altered:
                params['instance_type'].filter.list = ['Shared Instance', 'Dedicated Instance']
                params['instance_type'].value = 'Shared Instance'
        else:
            params['instance_type'].filter.list = ['Dedicated Instance']
            params['instance_type'].value = 'Dedicated Instance'
            if params['raster_url'].value.lower().endswith('.crf'):
                params['instance_type'].filter.list = ['Shared Instance']
                params['instance_type'].value = 'Shared Instance'
        if not params['service_running_status'].altered:
            params['service_running_status'].value = 'Keep Current Status'
            params['service_running_status'].filter.list = ['Keep Current Status', 'Start',  'Stop']
        if not params['service_name'].altered:
            params['service_name'].value = ''
        if params['folder_name'].altered and not params['folder_name'].hasBeenValidated:
            folder_names = params['folder_name'].filter.list
            if params['folder_name'].valueAsText not in folder_names:
                folder_names.append(params['folder_name'].valueAsText)
                params['folder_name'].filter.list = folder_names
            if params['action'].valueAsText != self.actions['create']:
                services = imagery_service.list_services(params['folder_name'].valueAsText)
                service_names = [service['serviceName'] for service in services]
                params['service_name'].value = service_names[0] if service_names else ''
                params['service_name'].filter.list = service_names if service_names else []
        if params['service_name'].altered and not params['service_name'].hasBeenValidated:
            if params['action'].valueAsText == self.actions['update']:
                get_service_data_response = imagery_service.get_service_data(params['service_name'].value,
                                                                                         params['folder_name'].value)
                if get_service_data_response.get('success'):
                    params['description'].value = get_service_data_response['service_data']['properties'].get('description')
                    params['update_data_path'].value = get_service_data_response['service_data']['properties'].get('path')
        if not params['action'].altered:
            params['action'].value = self.actions['create']
        if params['action'].altered and not params['action'].hasBeenValidated:
            if params['action'].valueAsText == self.actions['delete']:
                self.enableParams([params['server'], params['service_name'],
                                   params['action'], params['folder_name']],
                                         parameters)
                services = imagery_service.list_services(params['folder_name'].value)
                service_names = [service['serviceName'] for service in services]
                params['service_name'].value = service_names[0] if service_names else ''
                params['service_name'].filter.list = service_names if service_names else []
            elif params['action'].valueAsText == self.actions['create']:
                params['service_name'].filter.list = []
                params['service_name'].value = ''
                self.enableParams(
                    [params['service_name'], params['folder_name'],
                     params['description'], params['action'],
                     params['copyright'], params['raster_url'],
                     params['instance_type'], params['server'],
                     params['add_item_to_AGOL']],
                    parameters)
            elif params['action'].valueAsText == self.actions['update']:
                self.enableParams(
                    [params['service_name'], params['description'],
                     params['folder_name'], params['server'],
                     params['service_running_status'],
                     params['update_data_path'], params['action']],
                    parameters)
                services = imagery_service.list_services(params['folder_name'].value)
                service_names = [service['serviceName'] for service in services]
                params['service_name'].value = service_names[0] if service_names else ''
                params['service_name'].filter.list = service_names if service_names else []

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        global error_message
        params = self.mapParams(parameters)
        if error_message:
            parameters[0].setErrorMessage(error_message)
        else:
            if params['action'].value == self.actions['delete']:
                imagery_service = ImageryServices(config_file=get_server_config_path(params['server'].valueAsText))
                services = imagery_service.list_services(params['folder_name'].value)
                service_names = [service['serviceName'] for service in services]
                if params['service_name'].value not in service_names:
                    params['service_name'].setErrorMessage("This service is invalid. Please refresh the tool to get the latest set of services.")
                else:
                    params['service_name'].clearMessage()
            else:
                params['service_name'].clearMessage()

    def get_data_type(self, raster_url):
        try:
            data_describe = arcpy.Describe(raster_url)
            if data_describe.format == 'AMD':
                return('md')
            else:
                return('img')
        except:
            return('md')

    def get_resampling_method_int(self, resampling_method):
        if resampling_method.lower() == 'nearest neighbor':
            return '0'
        elif resampling_method.lower() == 'bilinear interpolation':
            return '1'
        elif resampling_method.lower() == 'cubic convolution':
            return '2'
        elif resampling_method.lower() == 'majority':
            return '3'
        else:
            return '1'
    
    def get_service_param_right_format(self, service_param):
        if type(service_param) == str:
            return ','.join(service_param.split(';'))
        return service_param

    def get_service_parameters(self, raster_url):
        try:
            data_describe = arcpy.Describe(raster_url)
            service_params =  {
                       "availableMensurationCapabilities": self.get_service_param_right_format(data_describe.availableMensurationCapabilities),
                       "allowedMensurationCapabilities": self.get_service_param_right_format(data_describe.allowedMensurationCapabilities),
                       "maxImageHeight": data_describe.maxImageHeight,
                       "allowedMosaicMethods": self.get_service_param_right_format(data_describe.allowedMosaicMethods),
                       "availableFields": self.get_service_param_right_format(data_describe.allowedFields),
                       "defaultCompressionQuality": data_describe.defaultCompressionQuality,
                       "defaultResamplingMethod": self.get_resampling_method_int(data_describe.defaultResamplingMethod),
                       "availableCompressions": self.get_service_param_right_format(data_describe.allowedCompressions),
                       "availableMosaicMethods": self.get_service_param_right_format(data_describe.availableMosaicMethods),
                       "allowedCompressions": self.get_service_param_right_format(data_describe.allowedCompressions),
                       "allowedFields": self.get_service_param_right_format(data_describe.allowedFields)

                   }
            return service_params
        except Exception as e:
            return{}

    def execute(self, parameters, messages):
        try:
            params = self.mapParams(parameters)
            config_file = get_server_config_path(params['server'].valueAsText)
            imagery_service = ImageryServices(config_file=config_file)
            if params['action'].valueAsText == self.actions['delete']:
                imagery_service.delete_service(params['service_name'].value, params['folder_name'].value, delete_source=False)
            elif params['action'].valueAsText == self.actions['create']:
                data_type = self.get_data_type(params['raster_url'].valueAsText)
                instance_type = params['instance_type'].value.lower().split()[0]
                if data_type ==  'md':
                    service_parameters = self.get_service_parameters(params['raster_url'].valueAsText)
                    create_response = imagery_service.create_service(params['folder_name'].value, params['service_name'].value,
                                                   params['raster_url'].valueAsText, params['description'].value,
                                                   params['copyright'].value, 'md', service_params=service_parameters,
                                                   instance_type=instance_type)
                else:
                    create_response = imagery_service.create_service(params['folder_name'].value, params['service_name'].value,
                                                   params['raster_url'].valueAsText, params['description'].value,
                                                   params['copyright'].value, 'img', instance_type=instance_type)
                if not create_response.get('success'):
                    arcpy.AddError(create_response.get('message'))
                    return
                if params['add_item_to_AGOL'].value:
                    config_json = {}
                    with open(config_file) as f:
                        config_json = json.load(f)
                    if config_json.get('agol') and config_json.get('agol').get('username') and config_json.get('agol').get('password'):
                        agol_token = imagery_service.generate_token(config_json['agol']['username'],
                                                                    config_json['agol']['password'],
                                                                    config_json['agol']['url'])
                        if params['folder_name'].value:
                            service_url = '{}/rest/services/{}/{}/ImageServer'.format(config_json.get('imageserver').get('url'),
                                                                                      params['folder_name'].valueAsText,
                                                                                      params['service_name'].valueAsText)
                        else:
                            service_url = '{}/rest/services/{}/ImageServer'.format(config_json.get('imageserver').get('url'),
                                                                                   params['service_name'].valueAsText)                            
                        item = {
                                        "type": "Image Service",
                                        "title": params['service_name'].valueAsText,
                                        "tags": ','.join([params['service_name'].valueAsText, 'ImageServer']),
                                        "description": params['description'].valueAsText,
                                        "url": service_url
                                }
                        add_item_response = imagery_service.add_item(agol_token, '', config_json['agol']['url'], config_json['agol']['username'], '', item)
                        if type(add_item_response) == dict and add_item_response.get('success') == False:
                            arcpy.AddError("Error in adding item to ArcGIS Online: {}".format(add_item_response.get('message')))
                    else:
                        arcpy.AddError("Please enter ArcGIS Online credentials in the server configuration file.")
            elif params['action'].valueAsText == self.actions['update']:
                start = None
                if params['service_running_status'].value.lower() == 'start':
                    start = True
                elif params['service_running_status'].value.lower() == 'stop':
                    start = False
                imagery_service.update_service(params['service_name'].value, params['folder_name'].value,
                               start=start, description=params['description'].value,
                               path=params['update_data_path'].value)
            imagery_service.close()
        except Exception as e:
            arcpy.AddError('Error occurred while trying to process the request. {}'.format(str(e)))
            imagery_service.close()
