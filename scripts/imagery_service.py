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
# Name: imagery_service.py
# Description: Utility class for publish, share, update, delete imagery services
# Version: 20180920
# Requirements: python.exe 3.6, arcpy library, solutionlog
# Required Arguments: N/A
# Optional Arguments: N/A
# Usage:
# Author: Esri Imagery Workflows Team
# ------------------------------------------------------------------------------

import sys
import os
import json
import requests
import time
scripts = os.path.dirname(os.path.realpath(__file__))

sys.path.append(scripts)
solutionlog = os.path.join((scripts),"SolutionsLog")
sys.path.append(solutionlog)
import logger
import arcpy

'''log status types enums
#const_general_text = 0
#const_warning_text = 1
#const_critical_text = 2
#const_status_text = 3'''


log = logger.Logger()
log.Project('imagery_service')
log.LogNamePrefix('imagery_service')
log.StartLog()
root_folder = os.path.dirname(
    os.path.dirname(os.path.dirname(logger.__file__)))
log_output_folder = os.path.join(root_folder, 'logs')
log.SetLogFolder(log_output_folder)
requests.packages.urllib3.disable_warnings()


class ImageryServices(object):

    def __init__(self, username=None, serverurl=None, portalurl=None, config_file=None):
        global config
        if not config_file:
            config_file = os.path.join(root_folder,
                                            'Parameter',
                                            'credentials',
                                            'credentials.json')

        try:
            with open(config_file) as f:
                config = json.load(f)
        except:
            config = None
        if config:
            self._portalurl = portalurl or config['portal']['url']
            self._username_cw = username or config['imageserver']['admin']['username']
            self._serverurl = serverurl or config['imageserver']['url']
        else:
            self._portalurl = portalurl
            self._username_cw = username
            self._serverurl = serverurl

    def delete_service(self, service_name,
                       folder_name, service_type='ImageServer',
                       item_type='Image Service',
                       delete_source=True):
        try:
            log.CreateCategory('DeleteService')
            if config['federated']:
                token = self.generate_token()
            else:
                token = self.generate_server_token()
            if(self._service_exists(self._serverurl,
                                    token,
                                    service_name,
                                    folder_name,
                                    service_type)):
                service_def = self._get_service_data(service_name, service_type,
                                                     token,
                                                     self._serverurl,
                                                     folder_name)
                if not service_def:
                    err_message = "Could not get service def "+ service_name
                    log.Message(err_message, log.const_critical_text)
                    return self._get_result_status(success=False,
                                                   message=err_message)
                if delete_source:
                    path = service_def['properties']['path'] if service_def else None
                if folder_name:
                    delete_url = "".join([self._serverurl, "/admin/services/",
                                          folder_name, "/", service_name, ".",
                                          service_type, "/delete"])
                else:
                    delete_url = "".join([self._serverurl, "/admin/services/",
                                          service_name, ".", service_type,
                                          "/delete"])
                params = {
                             'token': token,
                             'f': 'json'
                        }
                log.Message("".join([service_name,
                                     " is going to be deleted!"]),
                            log.const_warning_text)
                response = requests.post(delete_url, data=params, verify=False)
                result_json = response.json()
                if result_json.get('status') == 'success':
                    log.Message("Successfully deleted service ",
                                log.const_general_text)
                    if config['federated']:
                        item = self._get_portal_item_by_id(token, self._portalurl,
                                                          service_def['portalProperties']['portalItems'][0]['itemID'])
                        if item:
                            delete_response = self._delete_portal_item(
                                                          token,
                                                          item.get('owner'),
                                                          item.get('id'),
                                                          self._portalurl)
                    if delete_source and path:
                        try:
                            arcpy.Delete_management(path)
                        except Exception as e:
                            log.Message(
                                ''.join(['Could not delete service data', str(e)]),
                                log.const_critical_text)
                    return self._get_result_status(success=True, message="")
                else:
                    err_messages = ['Could not delete service.']
                    err_messages.extend(result_json.get('messages'))
                    err_message = ' '.join(err_messages)
                    log.Message(err_message, log.const_critical_text)
                    return self._get_result_status(success=False,
                                                   message=err_message)
            else:
                err_mess = ''.join(["Service ",
                                    service_name,
                                    " not found!"])
                log.Message(err_mess,
                            log.const_critical_text)
                return self._get_result_status(success=False,
                                               message=err_mess)
        except Exception as e:
            error_message = "".join(["Error in delete service ", service_name])
            log.Message(error_message + str(e), log.const_critical_text)
            return self._get_result_status(success=False,
                                           message=error_message)

    def publish_image_service(self,
                              service_name,
                              folder_name,
                              service_type,
                              group_name,
                              path,
                              item_type,
                              description,
                              copyright,
                              tags, datatype,
                              portal_folder_name=None,
                              group_id=None,
                              item_additional_params=None,
                              service_params=None):
        try:
            log.CreateCategory('PublishService')
            token = self._generate_token(self._username_cw,
                                         config['imageserver']['admin']['password'],
                                         self._portalurl)
            if not self._service_exists(self._serverurl,
                                        token,
                                        service_name,
                                        folder_name,
                                        service_type):
                if not group_id:
                    if group_name:
                        group_id = self._get_group_id(token,
                                                      self._portalurl,
                                                      group_name)
                create_response = self.create_service(folder_name,
                                                       service_name,
                                                       path,
                                                       description,
                                                       copyright,
                                                       datatype,
                                                       service_params=service_params)
                if not create_response['success']:
                    err_message = ''.join(['Could not create service '
                                           'on server ',
                                           create_response['message']])
                    return self._get_result_status(success=False,
                                                   message=err_message)
                service_def = self._get_service_data(service_name, service_type,
                                                     token,
                                                     self._serverurl,
                                                     folder_name)
                if not service_def:
                    err_message = "Could not get service def "+ service_name
                    log.Message(err_message, log.const_critical_text)
                    return self._get_result_status(success=False,
                                                   message=err_message)
                folder_id = ''
                if portal_folder_name:
                    folder_id = self._get_portal_folder_id(token,
                                                           self._portalurl,
                                                           portal_folder_name,
                                                           self._username_cw)
                if service_def['portalProperties']['portalItems'] and \
                   service_def['portalProperties']['portalItems'][0] and \
                   service_def['portalProperties']['portalItems'][0]['itemID']:
                    item = self._get_portal_item_by_id(token,
                                                       self._portalurl,
                                                       service_def['portalProperties']['portalItems'][0]['itemID'])
                    if not item:
                        err_message = "Error creating portal item"
                        log.Message(err_message,
                                    log.const_critical_text)
                        return self._get_result_status(success=False,
                                                   message=err_message)
                else:
                    service_url = self._serverurl + '/rest/services/' + service_name + '/' + service_type
                    if folder_name:
                        service_url = self._serverurl + '/rest/services/' + service_name + '/' + folder_name + '/' + service_type
                    item_params = {
                                        "type": item_type,
                                        "title": service_name,
                                        "tags": tags,
                                        "description": description,
                                        "url": service_url
                                  }
                    item_id = self.add_item(token, '', self._portalurl, self._username_cw,
                                             folder_id,
                                             item_params)
                    self._update_service_item_id(token, self._serverurl,
                                                 service_name,
                                                 folder_name,
                                                 service_type,
                                                 item_id)

                if portal_folder_name:
                    move_item_response = self._move_items(folder_id,
                                                          [item.get('id')],
                                                          token,
                                                          self._portalurl,
                                                          self._username_cw)
                    if not move_item_response['success']:
                        err_message = ''.join(['Could not move portal item '
                                               'to folder ',
                                               move_item_response['message']])
                        return self._get_result_status(success=False,
                                                       message=err_message)
                update_item_response = self._update_item(tags,
                                                         token,
                                                         self._portalurl,
                                                         self._username_cw,
                                                         item.get('id'),
                                                         description,
                                                         additional_params=item_additional_params)
                if not update_item_response['success']:
                    err_message = ''.join(['Could not add tags/description'
                                           ' to item ',
                                           update_item_response['message']])
                    return self._get_result_status(success=False,
                                                   message=err_message)
                if group_id:
                    share_response = self._share_service_with_group(
                                                            self._portalurl,
                                                            self._username_cw,
                                                            item.get('id'),
                                                            group_id,
                                                            token)
                    if not share_response['success']:
                        err_message = ''.join(['Could not share service'
                                               ' with organization ',
                                               share_response['message']])
                        return self._get_result_status(success=False,
                                                       message=err_message)
                item_url = (self._portalurl +
                            "/home/item.html?id=" +
                            item.get('id'))
                success_msg = "".join([
                    "Successfully published raster dataset ",
                    service_name])
                log.Message(success_msg, log.const_general_text)
                return self._get_result_status(success=True,
                                               message="", item_url=item_url)

            else:
                log.Message("Service exists already!", log.const_critical_text)
                return self._get_result_status(success=False,
                                               message='Service exists'
                                               ' already!')
        except Exception as e:
            err_message = "".join(["Error in publish image service ",
                                   service_name])
            log.Message(err_message + str(e), log.const_critical_text)
            return self._get_result_status(success=False, message=err_message)

    def share_service_to_external_portal(
                                    self,
                                    dest_username,
                                    dest_password,
                                    service_name,
                                    folder_name,
                                    dest_folder_name=None,
                                    dest_group_name=None,
                                    dest_portalurl="https://www.arcgis.com",
                                    service_type="ImageServer",
                                    item_type="Image Service",
                                    service_username=None,
                                    service_password=None,
                                    dest_token=None):
        try:
            log.CreateCategory('ShareServiceToExternalPortal')
            token = self._generate_token(self._username_cw,
                                         config['imageserver']['admin']['password'],
                                         self._portalurl)
            if self._service_exists(self._serverurl,
                                    token,
                                    service_name,
                                    folder_name,
                                    service_type):
                if not dest_token:
                    dest_token = self._generate_token(dest_username,
                                                      dest_password,
                                                      dest_portalurl)
                elif len(dest_token) < 5:
                    dest_token = self._generate_token(dest_username,
                                                      dest_password,
                                                      dest_portalurl)
                folder_id = self._get_portal_folder_id(token,
                                                       self._portalurl,
                                                       folder_name,
                                                       self._username_cw)
                service_def = self._get_service_data(service_name,
                                                     service_type,
                                                     token,
                                                     self._serverurl,
                                                     folder_name)
                if not service_def:
                    err_message = "Could not get service def "+ service_name
                    log.Message(err_message, log.const_critical_text)
                    return self._get_result_status(success=False,
                                                   message=err_message)
                item = self._get_portal_item_by_id(token,
                                                   self._portalurl,
                                                   service_def['portalProperties']['portalItems'][0]['itemID'])
                if not item:
                    log.Message(
                        "Could not retrieve portal item ",
                        log.const_critical_text)
                    return self._get_result_status(
                        success=False,
                        message='Could not retrieve portal item')
                item_data = self._get_item_data(self._portalurl,
                                                token,
                                                item['id'])
                dest_folder_id = ''
                if dest_folder_name:
                    dest_folder_id = self._get_portal_folder_id(
                        dest_token,
                        dest_portalurl,
                        dest_folder_name,
                        dest_username)
                    if not dest_folder_id:
                        dest_folder_id = self._create_portal_folder(
                                                   dest_folder_name,
                                                   dest_token,
                                                   dest_portalurl,
                                                   dest_username)
                        if not dest_folder_id:
                            log.Message(
                                "Could not create portal folder ",
                                log.const_critical_text)
                            return self._get_result_status(
                                success=False,
                                message='Could not create portal folder')
                dest_item_id = self.add_item(dest_token,
                                              item_data,
                                              dest_portalurl,
                                              dest_username,
                                              dest_folder_id,
                                              item,
                                              service_username=service_username,
                                              service_password=service_password)
                if dest_group_name:
                    dest_group_id = self._get_group_id(dest_token,
                                                       dest_portalurl,
                                                       dest_group_name,
                                                       dest_username)
                    share_response = self._share_service_with_group(
                        dest_portalurl,
                        dest_username,
                        dest_item_id,
                        dest_group_id,
                        dest_token)
                    if not share_response['success']:
                        return self._get_result_status(
                            success=False,
                            message=''.join([
                                'Could not share service to external group ',
                                share_response['message']]))
                log.Message(
                    "".join([
                        "Successfully shared service to external portal ",
                        service_name]),
                    log.const_general_text)
                return self._get_result_status(success=True, message='')
            else:
                log.Message("Service does not exist", log.const_critical_text)
                return self._get_result_status(
                    success=False,
                    message='Service does not exist')
        except Exception as e:
            log.Message(
                "".join([
                    "Error in sharing service ",
                    service_name,
                    "to external portal ",
                    str(e)]),
                log.const_critical_text)
            return self._get_result_status(
                success=False,
                message='Could not share service to external portal')

    def get_service_data(self, service_name, folder_name):
        try:
            if config['federated']:
                token = self.generate_token()
            else:
                token = self.generate_server_token()
            service_def = self._get_service_data(service_name, 'ImageServer',
                                                 token, self._serverurl,
                                                 folder_name)
            return self._get_result_status(success=True, message='', service_data=service_def)
        except Exception as e:
            return self._get_result_status(success=False,
                                           message='Error in getting service data for {}. {}'.format(service_name, str(e)))

    def update_service(self,
                       service_name,
                       folder_name,
                       service_type='ImageServer',
                       start=None,
                       tags=None,
                       description=None,
                       public=None,
                       path=None,
                       item_type='Image Service',
                       delete_old_source=True,
                       item_additional_params=None,
                       service_params=None):
        try:
            log.CreateCategory('UpdateService')
            if config['federated']:
                token = self.generate_token()
            else:
                token = self.generate_server_token()
            if(self._service_exists(self._serverurl,
                                    token,
                                    service_name,
                                    folder_name,
                                    service_type)):
                service_def = self._get_service_data(service_name,
                                                     service_type,
                                                     token,
                                                     self._serverurl,
                                                     folder_name)
                if not service_def:
                    err_message = "Could not get service def "+ service_name
                    log.Message(err_message, log.const_critical_text)
                    return self._get_result_status(success=False,
                                                   message=err_message)
                item_id = None
                if service_def.get('portalProperties') and service_def.get('portalProperties').get('portalItems'):
                    item_id = service_def['portalProperties']['portalItems'][0]['itemID']
                if service_params:
                    if not all(service_param_key in service_def['properties'] for service_param_key in service_params):
                        return self._get_result_status(success=False,
                                                       message="Error in the additional server definition parmaters passed. Please check if the parameters passed are valid.")
                    for key in service_params:
                        if key in service_def['properties']:
                            service_def['properties'][key] = service_params[key]
                if description:
                    service_def['description'] = description
                    service_def['properties']['description'] = description
                if path:
                    old_path = service_def['properties']['path'] if service_def else None
                    service_def['properties']['path'] = path
                if config['federated'] and item_id:
                    if public is not None:
                        share_response = self._share_item(item_id,
                                                          self._portalurl,
                                                          self._username_cw,
                                                          token,
                                                          public)
                        if not share_response['success']:
                            return self._get_result_status(
                                success=False,
                                message=''.join([
                                    'Could not make item private/public',
                                    share_response['message']]))
                if folder_name:
                    update_url = ''.join([
                        self._serverurl,
                        "/admin/services/",
                        folder_name, "/",
                        service_name, '.',
                        service_type,
                        '/edit'])
                else:
                    update_url = ''.join([self._serverurl,
                                          "/admin/services/",
                                          service_name, '.',
                                          service_type,
                                          '/edit'])
                params = {
                    'f': 'json',
                    'token': token,
                    'service': json.dumps(service_def)
                }
                results = requests.post(update_url, data=params, verify=False)
                result_json = results.json()
                if result_json.get('status') == 'success':
                    log.Message(
                        "Successfully updated service " + service_name,
                        log.const_general_text)
                else:
                    err_messages = ['Could not update service.']
                    err_messages.extend(result_json.get('messages'))
                    err_message = ' '.join(err_messages)
                    log.Message(err_message, log.const_critical_text)
                    return self._get_result_status(success=False,
                                                   message=err_message)
                if config['federated'] and item_id:
                    update_item_response = self._update_item(tags,
                                                             token,
                                                             self._portalurl,
                                                             self._username_cw,
                                                             item_id,
                                                             description,
                                                             additional_params=item_additional_params)
                    if not update_item_response['success']:
                        return self._get_result_status(
                            success=False,
                            message=''.join([
                                'Could not update portal item ',
                                update_item_response['message']]))
                if start is not None:
                    if start:
                        if not self._start_service(service_name,
                                                   service_type,
                                                   self._serverurl,
                                                   token,
                                                   folder_name):
                            return self._get_result_status(
                                success=False,
                                message="Could not start service")
                    else:
                        if not self._stop_service(service_name,
                                                  service_type,
                                                  self._serverurl,
                                                  token,
                                                  folder_name):
                            return self._get_result_status(
                                success=False,
                                message="Could not stop service")
                if path and delete_old_source and old_path:
                    try:
                        arcpy.Delete_management(old_path)
                    except Exception as e:
                        log.Message(
                                ''.join(['Could not delete service data', str(e)]),
                                log.const_critical_text)
                log.Message(
                    "".join([
                        "Service ",
                        service_name,
                        " updated succesfully. "]),
                    log.const_general_text)
                service_status = self._get_service_status(service_name,
                                                          service_type,
                                                          self._serverurl,
                                                          token, folder_name)
                if config['federated'] and item_id:
                    item_url = (self._portalurl +
                                            "/home/item.html?id=" +
                                            item_id)
                    return self._get_result_status(success=True,
                                                   message='',
                                                   service_status=service_status,
                                                   item_url=item_url)
                return self._get_result_status(success=True,
                                                   message='',
                                                   service_status=service_status)
            else:
                log.Message("Service does not exist", log.const_critical_text)
                return self._get_result_status(
                    success=False,
                    message='Service does not exist')
        except Exception as e:
            log.Message(
                "".join([
                    "Unable to update service ",
                    service_name]),
                log.const_critical_text)
            return self._get_result_status(
                success=False,
                message="Unable to update service ")

    def delete_portal_item(self, item_id):
        try:
            log.CreateCategory('DeletePortalItem')
            token = self._generate_token(self._username_cw,
                                         config['imageserver']['admin']['password'],
                                         self._portalurl)
            item = self._get_portal_item_by_id(token, self._portalurl, item_id)
            if item:
                delete_response = self._delete_portal_item(
                                    token,
                                    item.get('owner'),
                                    item.get('id'),
                                    self._portalurl)
        except Exception as e:
            err_message = "".join([
                "Error in deleting portal item ", item_id])
            log.Message(err_message, log.const_critical_text)

    def list_services(self, folder_name='', service_type='ImageServer'):
        try:
            log.CreateCategory('ListServices')
            if config['federated']:
                token = self.generate_token()
            else:
                token = self.generate_server_token()
            if folder_name:
                list_url = "".join([
                    self._serverurl,
                    "/admin/services/",
                    folder_name])
            else:
                list_url = "".join([self._serverurl, "/admin/services/"])
            params = {
                'f': 'json',
                'token': token
            }
            response = requests.get(list_url, params=params, verify=False)
            services = response.json().get('services')
            if services:
                if not service_type:
                    return services
                return [service for service in services
                        if service.get('type') == service_type]
            else:
                return []
        except Exception as e:
            err_message = "".join([
                "Error in listing services for user ",
                self._username_cw])
            log.Message(err_message, log.const_critical_text)

    def start_service(self, service_name, service_type, folder_name=''):
        log.CreateCategory('StartService')
        if config['federated']:
            token = self.generate_token()
        else:
            token = self.generate_server_token()
        return self._start_service(service_name,
                                   service_type,
                                   self._serverurl,
                                   token,
                                   folder_name)

    def stop_service(self, service_name, service_type, folder_name=''):
        log.CreateCategory('StopService')
        if config['federated']:
            token = self.generate_token()
        else:
            token = self.generate_server_token()
        return self._stop_service(service_name,
                                  service_type,
                                  self._serverurl,
                                  token,
                                  folder_name)

    def get_service_status(self, service_name, service_type, folder_name=''):
        log.CreateCategory('GetServiceStatus')
        if config['federated']:
            token = self.generate_token()
        else:
            self.generate_server_token()
        return self._get_service_status(service_name,
                                        service_type,
                                        self._serverurl,
                                        token, folder_name)

    def get_folder_items_count(self, folder_name):
        try:
            log.CreateCategory('GetFolderItemsCount')
            token = self._generate_token(self._username_cw,
                                         config['imageserver']['admin']['password'],
                                         self._portalurl)
            folder_id = self._get_portal_folder_id(token, self._portalurl,
                                                   folder_name,
                                                   self._username_cw)
            items = self._get_portal_folder_items(token,
                                                  self._portalurl, folder_id)
            return self._get_result_status(success=True,
                                           message='',
                                           count=int(len(items)))
        except Exception as e:
            log.Message(
                "Error getting number of items in folder " + folder_name,
                log.const_critical_text)
            return self._get_result_status(
                success=False,
                message="Error getting number of "
                "items in folder " + folder_name)

    def get_all_server_folders(self):
        try:
            log.CreateCategory('GetAllServerFolders')
            if config['federated']:
                token = self.generate_token()
            else:
                token = self.generate_server_token()
            status_url = "".join([self._serverurl, "/admin/services/"])
            params = {
                'f': 'pjson',
                'token': token
            }
            response = requests.get(status_url, params=params, verify=False)
            folders = response.json()['foldersDetail']
            folders_minus_default_folders = [folder for folder in folders
                                             if not folder.get('isDefault')]
            return self._get_result_status(success=True, message='',
                                    folders=folders_minus_default_folders)
        except Exception as e:
            log.Message("Error getting all folders", log.const_critical_text)
            return self._get_result_status(success=False,
                                           message="Error getting all folders")

    def create_server_folder(self, folder_name):
        try:
            log.CreateCategory('CreateServerFolder')
            if config['federated']:
                token = self.generate_token()
            else:
                token = self.generate_server_token()
            create_url = ''.join([
                self._serverurl,
                "/admin/services/createFolder"])
            params = {
                'f': 'pjson',
                'token': token,
                'folderName': folder_name
            }
            response = requests.post(create_url, data=params, verify=False)
            response_json = response.json()
            if response_json.get('status') == 'success':
                log.Message(
                    'Successfully created folder ' + folder_name,
                    log.const_general_text)
                return self._get_result_status(success=True, message='')
            else:
                error_message = ' '.join(response_json.get('messages') or [])
                log.Message(
                    "Error creating folder. " + error_message,
                    log.const_critical_text)
                return self._get_result_status(
                    success=False,
                    message=error_message)
        except Exception as e:
            log.Message(
                "Something went wrong while creating the folder.",
                log.const_critical_text)
            return self._get_result_status(
                success=False,
                message='Something went wrong while creating the folder.')

    def delete_server_folder(self, folder_name, admin_token):
        try:
            log.CreateCategory('DeleteServerFolder')
            create_url = ''.join([
                self._serverurl,
                "/admin/services/",
                folder_name,
                "/deleteFolder"])
            params = {
                'f': 'pjson',
                'token': admin_token
            }
            response = requests.post(create_url, data=params, verify=False)
            response_json = response.json()
            if response_json.get('status') == 'success':
                log.Message(
                    'Successfully deleted folder ' + folder_name,
                    log.const_general_text)
                return self._get_result_status(success=True, message='')
            else:
                error_message = ' '.join(response_json.get('messages') or [])
                log.Message(
                    "Error deleting folder. " + error_message,
                    log.const_critical_text)
                return self._get_result_status(success=False,
                                               message=error_message)
        except Exception as e:
            log.Message(
                "Something went wrong while deleting the folder.",
                log.const_critical_text)
            return self._get_result_status(
                success=False,
                message='Something went wrong while creating the folder.')

    def get_directory_path(self, directory_name):
        try:
            if config('federated'):
                token = self.generate_token()
            else:
                token = self.generate_server_token()
            path, virtual_path = self._get_directory_path(directory_name,
                                            token,
                                            self._serverurl)
            log.Message(
                "Directory path of " + directory_name + " is " + path,
                log.const_general_text)
            log.Message(
                "Virtual path of " + directory_name + " is " + virtual_path,
                log.const_general_text)
            return self._get_result_status(success=True,
                                           message="",
                                           path=path,
                                           virtual_path=virtual_path)
        except Exception as e:
            log.Message(
                "Error in getting directory path.",
                log.const_critical_text)
            return self._get_result_status(
                success=False,
                message="Error in getting directory path.")

    def get_service_last_modified(self,
                                  service_name,
                                  service_type,
                                  folder_name):
        try:
            log.CreateCategory('GetServiceLastModified')
            if config['federated']:
                token = self.generate_token()
            else:
                token = self.generate_server_token()
            lifecycle_infos = self._get_lifecycle_infos(service_type,
                                                        service_name,
                                                        folder_name,
                                                        self._serverurl,
                                                        token)
            return self._get_result_status(
                success=True,
                message='',
                last_modified=lifecycle_infos.get('lastmodified'))
        except Exception as e:
            log.Message(
                "Error while getting last modified of service " + service_name,
                log.const_critical_text)
            return self._get_result_status(
                success=False,
                message=('Error getting last modified of service ' +
                         service_name))

    def can_access_group(self, group_name, token):
        try:
            token = token or self._generate_token(self._username_cw,
                                                  config['imageserver']['admin']['password'],
                                                  self._portalurl)
            group = self._get_group(token, self._portalurl,
                                    group_name)
            if not group:
                return self._get_result_status(success=False,
                                               message='Group not found!')
            return self._get_result_status(success=True,
                                           message='')
        except Exception as e:
            log.Message("Error checking access to group " + group_name,
                        log.const_critical_text)
            return self._get_result_status(
                                     success=False,
                                     message='Error checking access to group',
                                     group=None)
    def update_portal_item(self, item_id,
                           description=None,
                           text=None,
                           tags=None,
                           additional_params=None):
        try:
            token = self._generate_token(self._username_cw,
                                         config['imageserver']['admin']['password'],
                                         self._portalurl)
            update_item_response = self._update_item(tags,
                                                     token,
                                                     self._portalurl,
                                                     self._username_cw,
                                                     item_id,
                                                     description, text,
                                                     additional_params=additional_params)
            if not update_item_response['success']:
                return self._get_result_status(
                    success=False,
                    message=''.join([
                        'Could not update portal item ',
                        update_item_response['message']]))
            return self._get_result_status(success=True,
                                           message='')
        except Exception as e:
            log.Message("Error updating item " + str(e),
                        log.const_critical_text)
            return self._get_result_status(
                 success=False,
                 message='Error updating item ' + item_name)

    def get_portal_item_data(self, item_id):
        try:
            token = self._generate_token(self._username_cw,
                                         config['imageserver']['admin']['password'],
                                         self._portalurl)
            item_data = self._get_item_data(self._portalurl, token, item_id)
            return self._get_result_status(success=True,
                                           message='',
                                           item_data=item_data)
        except Exception as e:
            log.Message("Error getting item data " + str(e),
                        log.const_critical_text)
            return self._get_result_status(
                success=False,
                message="Error getting item data")

    def generate_token(self, username=None, password=None, portalurl=None):
        try:
            if not username:
                username = config['portal']['admin']['username']
                password = config['portal']['admin']['password']
                portalurl=config['portal']['url']
            return self._generate_token(username=username,
                                        password=password,
                                        portalurl=portalurl)
        except Exception as e:
            log.Message("Error generating token" + str(e),
                        log.const_critical_text)
            return self._get_result_status(
                        success=False,
                        message="Error getting token.")

    def get_item(self, item_name, item_type, folder_name,
                 portalurl=None,
                 token=None,
                 username=None):
        try:
            if not token:
                token = self._generate_token(self._username_cw,
                                             config['imageserver']['admin']['password'],
                                             self._portalurl)
                portalurl = self._portalurl
                username = self._username_cw
            folder_id = None
            if folder_name:
                folder_id = self._get_portal_folder_id(token, portalurl, folder_name,
                                               username)
            return self._get_item(token, item_name, portalurl,
                                      item_type,
                                      folder_id)
        except Exception as e:
            log.Message("Error getting item " + str(e),
                                log.const_critical_text)
            return self._get_result_status(
                        success=False,
                        message="Error getting item")

    def edit_item_info(self, service_name,
                       service_type,
                       folder_name=None,
                       **info_params):
        try:
            token = self._generate_token(self._username_cw,
                                         config['imageserver']['admin']['password'],
                                         self._portalurl)
            if folder_name:
                info_url = "".join([self._serverurl,
                                      "/admin/services/",
                                      folder_name, "/",
                                      service_name, ".",
                                      service_type, "/iteminfo/edit"])
            else:
                info_url = "".join([self._serverurl,
                                      "/admin/services/",
                                      service_name, ".",
                                      service_type, "/iteminfo/edit"])
            params = {
                'f': 'pjson',
                'token': token,
                'serviceItemInfo': json.dumps(info_params)
            }
            response = requests.post(info_url, data=params, verify=False)
            response_json = response.json()
            if response_json.get('status') == 'success':
                return self._get_result_status(success=True, message='')
            else:
                return self._get_result_status(success=False,
                                               message=' '.join(response_json.get('messages')))
        except Exception as e:
            log.Message("Error editing item info " + str(e),
                        log.const_critical_text)
            return self._get_result_status(success=False,
                                           message="Error editing item info")

    def share_item_with_group(self,
                              username,
                              item_id,
                              group_id,
                              portalurl=None,
                              token=None):
        try:
            if not portalurl:
                portalurl = self._portalurl
                token = self._generate_token(self._username_cw,
                                             config['imageserver']['admin']['password'],
                                             self._portalurl)
            share_response = self._share_service_with_group(
                portalurl,
                username,
                item_id,
                group_id,
                token)
            if not share_response['success']:
                return self._get_result_status(
                    success=False,
                    message=''.join([
                        'Could not share service to external group ',
                        share_response['message']]))
            return self._get_result_status(success=True, message='')
        except Exception as e:
            log.Message("Error sharing item with group " + str(e),
                                log.const_critical_text)
            return self._get_result_status(success=False,
                                           message="Error sharing item with group")    

    def _update_service_item_id(self,
                                token,
                                serverurl,
                                service_name,
                                folder_name,
                                service_type,
                                item_id):
        try:
            log.CreateCategory('UpdateServiceItemId')
            if(self._service_exists(serverurl,
                                    token,
                                    service_name,
                                    folder_name,
                                    service_type)):
                service_def = self._get_service_data(service_name,
                                                     service_type,
                                                     token,
                                                     serverurl,
                                                     folder_name)
                if not service_def:
                    err_message = "Could not get service def "+ service_name
                    log.Message(err_message, log.const_critical_text)
                    return self._get_result_status(success=False,
                                                   message=err_message)
                if type(service_def['portalProperties']['portalItems']) == list:
                    service_def['portalProperties']['portalItems'].append({'itemID': item_id, 'type': service_type})
                if folder_name:
                    update_url = ''.join([
                        serverurl,
                        "/admin/services/",
                        folder_name, "/",
                        service_name, '.',
                        service_type,
                        '/edit'])
                else:
                    update_url = ''.join([serverurl,
                                          "/admin/services/",
                                          service_name, '.',
                                          service_type,
                                          '/edit'])
                params = {
                    'f': 'json',
                    'token': token,
                    'service': json.dumps(service_def)
                }
                results = requests.post(update_url, data=params, verify=False)
                result_json = results.json()
                if result_json.get('status') == 'success':
                    log.Message(
                        "Successfully updated service item id " + service_name,
                        log.const_general_text)
                else:
                    err_messages = ['Could not update service.']
                    err_messages.extend(result_json.get('messages'))
                    err_message = ' '.join(err_messages)
                    log.Message(err_message, log.const_critical_text)
                    return self._get_result_status(success=False,
                                                   message=err_message)
                return self._get_result_status(success=True,
                                               message='',
                                               service_status=service_status,
                                               item_url=item_url)
            else:
                log.Message("Service does not exist", log.const_critical_text)
                return self._get_result_status(
                    success=False,
                    message='Service does not exist')
        except Exception as e:
            log.Message(
                "".join([
                    "Unable to update service ",
                    service_name]),
                log.const_critical_text)
            return self._get_result_status(
                success=False,
                message="Unable to update service ")

    def _get_service_data(self,
                          service_name,
                          service_type,
                          token,
                          serverurl,
                          folder_name):
        try:
            if folder_name:
                status_url = "".join([serverurl,
                                      "/admin/services/",
                                      folder_name, "/",
                                      service_name, ".", service_type])
            else:
                status_url = "".join([serverurl,
                                      "/admin/services/",
                                      service_name, ".", service_type])
            params = {
                'f': 'pjson',
                'token': token
            }
            response = requests.get(status_url, params=params, verify=False)
            return response.json()
        except Exception as e:
            err_message = "".join(["Error in getting data for ", service_name])
            log.Message(err_message, log.const_critical_text)

    def _get_lifecycle_infos(self,
                             service_type,
                             service_name,
                             folder_name,
                             serverurl,
                             token):
        try:
            if folder_name:
                status_url = "".join([serverurl,
                                      "/admin/services/",
                                      folder_name, "/",
                                      service_name, ".",
                                      service_type, "/lifecycleinfos"])
            else:
                status_url = "".join([serverurl,
                                      "/admin/services/",
                                      service_name, ".",
                                      service_type, "/lifecycleinfos"])
            params = {
                'f': 'pjson',
                'token': token
            }
            response = requests.get(status_url, params=params, verify=False)
            return response.json()
        except Exception as e:
            err_message = "".join(["Error in getting data for ", service_name])
            log.Message(err_message, log.const_critical_text)

    def _get_service_status(self,
                            service_name,
                            service_type,
                            serverurl,
                            token, folder_name):
        try:
            if folder_name:
                status_url = "".join([serverurl,
                                      "/admin/services/",
                                      folder_name, "/",
                                      service_name, ".",
                                      service_type, "/status"])
            else:
                status_url = "".join([serverurl,
                                      "/admin/services/",
                                      service_name, ".",
                                      service_type, "/status"])
            params = {
                'f': 'pjson',
                'token': token
            }
            response = requests.post(status_url, data=params, verify=False)
            return response.json()['realTimeState']
        except Exception as e:
            err_message = "".join([
                "Error in getting status for ",
                service_name])
            log.Message(err_message, log.const_critical_text)

    def _start_service(self,
                       service_name,
                       service_type,
                       serverurl,
                       token,
                       folder_name):
        try:
            if folder_name:
                start_url = "".join([serverurl,
                                     "/admin/services/",
                                     folder_name, "/",
                                     service_name, ".",
                                     service_type, "/start"])
            else:
                start_url = "".join([serverurl,
                                     "/admin/services/",
                                     service_name, ".",
                                     service_type, "/start"])
            params = {
                'f': 'json',
                'token': token
            }
            response = requests.post(start_url, data=params, verify=False)
            response.json()
            return True
        except Exception as e:
            err_message = "".join(["Error in starting service ", service_name])
            log.Message(err_message, log.const_critical_text)
            return False

    def _stop_service(self,
                      service_name,
                      service_type,
                      serverurl, token, folder_name):
        try:
            if folder_name:
                stop_url = "".join([serverurl,
                                    "/admin/services/",
                                    folder_name, "/",
                                    service_name, ".",
                                    service_type, "/stop"])
            else:
                stop = "".join([serverurl,
                                "/admin/services/",
                                service_name, ".",
                                service_type, "/stop"])
            params = {
                'f': 'json',
                'token': token
            }
            response = requests.post(stop_url, data=params, verify=False)
            response.json()
            return True
        except Exception as e:
            err_message = "".join([
                "Error in stopping service ",
                service_name])
            log.Message(err_message, log.const_critical_text)
            return False

    def _service_exists(self,
                        serverurl,
                        token,
                        service_name,
                        folder_name,
                        service_type):
        exists_url = "".join([serverurl, "/admin/services/exists"])
        params = {
            'folderName': folder_name,
            'serviceName': service_name,
            'type': service_type,
            'f': 'json',
            'token': token
        }
        response = requests.post(exists_url, data=params, verify=False)
        if(response.json().get('status') != "error"):
            return response.json().get('exists')
        else:
            messages_list = ','.join(response.json().get('messages'))
            log.Message(
                ''.join([
                    'Error in exists_service for service ',
                    service_name, messages_list]),
                log.const_critical_text)

    def add_item(self, token, data, portalurl, username, folder_id, item,
                  service_username=None,
                  service_password=None):
        try:
            if not folder_id:
                add_item_url = (portalurl +
                                        "/sharing/rest/content/users/" +
                                        username +
                                        "/addItem")
            else:
                add_item_url = (portalurl +
                            "/sharing/rest/content/users/" +
                            username +
                            "/" +
                            folder_id +
                            "/addItem")
            params = {
                'token': token,
                'text': data,
                'f': 'json'
            }
            params.update(item)
            result = requests.post(add_item_url, data=params)
            return result.json()['id']
        except Exception as e:
            log.Message(
                "Error while adding item "+str(e),
                log.const_critical_text)
            return self._get_result_status(success=False,
                                            message="Error while adding item ")            

    def _move_items(self, folder_id, item_ids, token, portalurl, username):
        move_item_url = (portalurl +
                         "/sharing/rest/content/users/" +
                         username +
                         "/moveItems")
        params = {
            'token': token,
            'folder': folder_id,
            'f': 'json',
            'items': item_ids
        }
        try:
            result = requests.post(move_item_url, data=params, verify=False)
            result_json = result.json()
            if(result_json.get('results') and
               result_json.get('results')[0] and
               result_json.get('results')[0].get('success')):
                log.Message(
                    "Successfully moved portal items ",
                    log.const_general_text)
                return self._get_result_status(success=True, message="")
            else:
                err_message = "Could not move portal items. "
                if(result_json.get('error') and
                   result_json.get('error').get('message')):
                    err_message = (err_message +
                                   result_json.get('error').get('message'))
                log.Message(err_message, log.const_critical_text)
                return self._get_result_status(success=False,
                                               message=err_message)
        except Exception as e:
            log.Message(
                "Error while moving item ",
                log.const_critical_text)
            return self._get_result_status(success=False,
                                           message="Error while moving item ")

    def _share_service_with_group(self,
                                  portalurl,
                                  username,
                                  item_id,
                                  group_id,
                                  token):
        share_url = (portalurl +
                     "/sharing/rest/content/users/" +
                     username +
                     "/shareItems")
        share_params = {
                "everyone": False,
                "org": False,
                "items": item_id,
                "groups": group_id,
                "confirmItemControl": True,
                "token": token,
                "f": "json"
            }
        try:
            results = requests.post(share_url, share_params, verify=False)
            result_json = results.json()
            if(result_json.get('results') and
               result_json.get('results')[0] and
               result_json.get('results')[0].get('success')):
                log.Message("Shared item with group ",
                            log.const_general_text)
                return self._get_result_status(success=True, message="")
            else:
                err_message = "Could not share item with group. "
                if(result_json.get('error') and
                   result_json.get('error').get('message')):
                    err_message = (err_message +
                                   result_json.get('error').get('message'))
                log.Message(err_message, log.const_critical_text)
                return self._get_result_status(success=False,
                                               message=err_message)
        except Exception as e:
            log.Message(
                    "Unable to share with group ",
                    log.const_critical_text)
            return self._get_result_status(
                    success=False,
                    message="Unable to share with group ")

    def _get_portal_folder_id(self, token, portalurl, folder_name, username):
        folders = self._list_all_portal_folders(username, token, portalurl)
        filtered_folders = [folder for folder in folders
                            if folder.get('title') == folder_name]
        if not filtered_folders:
            log.Message(
                "".join([folder_name, " not found!"]),
                log.const_critical_text)
            return None
        return filtered_folders[0]['id']

    def _get_portal_folder_name(self, token, portalurl, folder_id, username):
        folders = self._list_all_portal_folders(username, token, portalurl)
        filtered_folders = [folder for folder in folders
                            if folder.get('id') == folder_id]
        if not filtered_folders:
            return None
        return filtered_folders[0]['title']

    def _get_item(self,
                  token,
                  service_name,
                  portalurl,
                  item_type,
                  folder_id=''):

        search_for_item_url = portalurl+"/sharing/rest/search"
        if folder_id:
            search_query = ('ownerfolder:' +
                            folder_id +
                            ' AND title:"' +
                            service_name +
                            '" AND type:"' +
                            item_type+'"')
        else:
            search_query = 'title:"'+service_name+'" AND type:"'+item_type+'"'
        search_params = {
            'q': search_query,
            'token': token,
            'f': 'pjson'
        }
        try:
            results = requests.post(search_for_item_url,
                                    search_params,
                                    verify=False)
            search_results = results.json()['results']
            exact_match_item = [item for item in search_results
                                if item['title'] == service_name]
            if not exact_match_item:
                log.Message("Item not found!", log.const_critical_text)
                return None
            item = exact_match_item[0]
            return item
        except Exception as e:
            err_message = "".join(["Error in getting item ", service_name])
            log.Message(err_message, log.const_critical_text)

    def _get_portal_item_by_id(self,
                               token,
                               portalurl,
                               item_id):

        search_for_item_url = portalurl+"/sharing/rest/search"
        search_query = 'id:'+item_id
        search_params = {
            'q': search_query,
            'token': token,
            'f': 'pjson'
        }
        try:
            results = requests.post(search_for_item_url,
                                    search_params,
                                    verify=False)
            search_results = results.json()['results']
            exact_match_item = [item for item in search_results
                                if item['id'] == item_id]
            if not exact_match_item:
                log.Message("Item not found!", log.const_critical_text)
                return None
            item = exact_match_item[0]
            return item
        except Exception as e:
            err_message = "".join(["Error in getting item by id ", item_id])
            log.Message(err_message, log.const_critical_text)

    def _get_portal_folder_items(self, token, portalurl, folder_id):
        try:
            search_for_item_url = portalurl + "/sharing/rest/search"
            query = "ownerfolder:" + folder_id
            search_params = {
                'q': query,
                'token': token,
                'f': 'json'
            }
            results = requests.post(search_for_item_url,
                                    search_params,
                                    verify=False)
            return results.json().get('results')
        except Exception as e:
            log.Message("Error in getting folder items")

    def _update_item(self,
                     tags,
                     token,
                     portalurl,
                     username,
                     item_id,
                     description,
                     text=None,
                     additional_params=None):
        update_item_url = (portalurl +
                           "/sharing/rest/content/users/" +
                           username +
                           "/items/" +
                           item_id +
                           "/update")
        params = {
            'token': token,
            'f': 'pjson'
        }
        if text is not None:
            params.update({'text': text})
        if additional_params is not None:
            params.update(additional_params)
        if tags is not None:
            params.update({'tags': tags})
        if description is not None:
            params.update({'description': description})
        try:
            results = requests.post(update_item_url, params, verify=False)
            result_json = results.json()
            if result_json.get('success'):
                log.Message(
                    "Successfully updated portal item ",
                    log.const_general_text)
                return self._get_result_status(success=True, message="")
            else:
                err_message = "Could not update portal item. "
                if(result_json.get('error') and
                   result_json.get('error').get('message')):
                    err_message = (err_message +
                                   result_json.get('error').get('message'))
                log.Message(err_message, log.const_critical_text)
                return self._get_result_status(success=False,
                                               message=err_message)
        except Exception as e:
            log.Message(
                "Error in deleting updating item " + item_id,
                log.const_critical_text)
            return self._get_result_status(
                success=False,
                message="Error in updating portal item ")

    def _delete_portal_item(self, token, username, item_id, portalurl):
        delete_url = "".join([
            self._portalurl,
            "/sharing/rest/content/users/",
            username,
            "/items/", item_id, "/delete"])
        try:
            params = {
                'token': token,
                'f': 'json'
            }
            result = requests.post(delete_url, data=params, verify=False)
            result_json = result.json()
            if result_json.get('success'):
                log.Message(
                    "Successfully deleted portal item ",
                    log.const_general_text)
                return self._get_result_status(success=True, message="")
            else:
                err_message = "Could not delete portal item. "
                if(result_json.get('error') and
                   result_json.get('error').get('message')):
                    err_message = (err_message +
                                   result_json.get('error').get('message'))
                log.Message(err_message, log.const_critical_text)
                return self._get_result_status(success=False,
                                               message=err_message)
        except Exception as e:
            log.Message(
                "Error in deleting portal item " + item_id,
                log.const_critical_text)
            return self._get_result_status(
                success=False,
                message="Error in deleting portal item " + item_id)

    def _get_item_data(self, portalurl, token, item_id):
        params = {
            'token': token,
            'f': 'json'
        }
        get_data_url = (portalurl +
                        "/sharing/rest/content/items/" +
                        item_id +
                        "/data")
        try:
            results = requests.get(get_data_url, params=params, verify=False)
            log.Message(
                "Successfully returned item data" + results.text,
                log.const_general_text)
            return results.text
        except Exception as e:
            err_message = "".join([
                "Exception in getting item data for item id ",
                item_id])
            log.Message(err_message, log.const_critical_text)

    def _generate_token(self, username, password, portalurl):
        '''Retrieves a token to be used with API requests.'''
        data = {
            'username': username,
            'password': password,
            'client': 'referer',
            'referer': portalurl,
            'expiration': 600,
            'f': 'json'
        }
        response = requests.post(
            ''.join([portalurl, '/sharing/rest/generateToken']),
            data=data,
            verify=False)
        log.Message('Generate_Token', log.const_general_text)
        try:
            jsonResponse = response.json()
            if 'token' in jsonResponse:
                log.Message("Token generated", log.const_general_text)
                return jsonResponse['token']
            elif 'error' in jsonResponse:
                log.Message(str(jsonResponse['error']['message']),
                            log.const_critical_text)
        except Exception as e:
            log_msg = "".join(["Unspecified Error ", str(e)])
            log.Message(log_msg, log.const_critical_text)

    def generate_server_token(self):
        username = config['imageserver']['admin']['username']
        password = config['imageserver']['admin']['password']
        serverurl=config['imageserver']['url']
        data = {
            'username': username,
            'password': password,
            'client': 'requestip',
            'referer': serverurl,
            'expiration': 600,
            'f': 'json'
        }
        response = requests.post(
            ''.join([serverurl, '/admin/generateToken']),
            data=data,
            verify=False)
        log.Message('Generate_Token', log.const_general_text)
        try:
            jsonResponse = response.json()
            if 'token' in jsonResponse:
                log.Message("Token generated", log.const_general_text)
                return jsonResponse['token']
            elif 'error' in jsonResponse:
                log.Message(str(jsonResponse['error']['message']),
                            log.const_critical_text)
        except Exception as e:
            log_msg = "".join(["Unspecified Error ", str(e)])
            log.Message(log_msg, log.const_critical_text)

    def _list_all_portal_folders(self, username, token, portalurl):
        try:
            data = {
                'token': token,
                'f': 'json'
            }
            response = requests.get(
                ''.join([portalurl, '/sharing/rest/content/users/', username]),
                params=data,
                verify=False)
            return response.json().get('folders')
        except Exception as e:
            err_message = "".join([
                "Error in listing folders for user ",
                username])
            log.Message(err_message, log.const_critical_text)

    def _create_portal_folder(self, folder_name, token, portalurl, username):
        try:
            create_url = ''.join([portalurl,
                                  '/sharing/rest/content/users/',
                                  username, '/createFolder'])
            data = {
                'folderName': folder_name,
                'title': folder_name,
                'token': token,
                'f': 'json'
            }
            response = requests.post(create_url, data=data, verify=False)
            response_json = response.json()
            if response_json.get('success'):
                log.Message('Created portal folder ' + folder_name,
                            log.const_critical_text)
                return response_json.get('folder').get('id')
            log.Message('Could not create portal folder ' + folder_name,
                        log.const_critical_text)
            return None
        except Exception as e:
            log.Message('Error in creating portal folder ' + folder_name,
                        log.const_critical_text)
            return None

    def _get_group(self, token, portalurl, group_name, username=None):
        try:
            search_for_group_url = (portalurl +
                                    "/sharing/rest/community/groups/")
            if username:
                search_query = 'owner:' + username + ' AND title:' + group_name
            else:
                search_query = 'title:' + group_name
            search_params = {
                'q': search_query,
                'token': token,
                'f': 'pjson',
                'num': 100
            }
            results = requests.post(search_for_group_url,
                                    search_params,
                                    verify=False)
            search_results = results.json()['results']
            exact_match_group = [group for group in search_results
                                 if group['title'] == group_name]
            if not exact_match_group:
                log.Message("Group not found!", log.const_critical_text)
                return None
            group = exact_match_group[0]
            return group
        except Exception as e:
            err_message = "".join(["Error getting group ", group_name, str(e)])
            log.Message(err_message, log.const_critical_text)

    def _get_group_id(self, token, portalurl, group_name, username=None):
        try:
            group = self._get_group(token, portalurl, group_name, username)
            if not group:
                log.Message("Group not found!", log.const_critical_text)
                return None
            return group.get('id')
        except Exception as e:
            err_message = "".join([
                "Error getting group id of group ",
                group_name])
            log.Message(err_message, log.const_critical_text)

    def _get_directory_path(self, directory_name, token, serverurl):
        try:
            cache_url = "".join([serverurl,
                                 "/admin/system/directories/",
                                 directory_name])
            params = {
                'f': 'pjson',
                'token': token
            }
            response = requests.get(cache_url, params=params, verify=False)
            return response.json().get('physicalPath'), response.json().get('virtualPath')
        except Exception as e:
            err_message = "".join([
                "Error in gettign directory path ",
                directory_name])
            log.Message(err_message, log.const_critical_text)

    def create_service(self,
                        folder_name,
                        service_name,
                        path, description,
                        copyright, datatype,
                        service_params=None,
                        instance_type='shared'):

        if config['federated']:
            token = self.generate_token()
        else:
            token = self.generate_server_token()
        serverurl = self._serverurl
        if folder_name:
            create_service_url = ''.join([serverurl,
                                          "/admin/services/",
                                          folder_name,
                                          '/createService'])
            self.create_server_folder(folder_name)            
        else:
            create_service_url = ''.join([serverurl,
                                          "/admin/services/",
                                          'createService'])
        service_def = ''
        jsonfile = 'template_service_definition_md'
        if datatype == 'md':
            jsonfile = 'template_service_definition_md'
        elif datatype == 'img':
            jsonfile = 'template_service_definition_img'
        with open(os.path.join(
                  root_folder,
                  'Parameter',
                  'json',
                  config['service_templates'][jsonfile])) as f:
            try:
                service_def = json.load(f)
            except:
                service_def = json.load(f)
        service_def['serviceName'] = service_name
        service_def['properties']['path'] = path
        service_def['description'] = description
        service_def['properties']['description'] = description
        service_def['properties']['copyright'] = copyright
        if instance_type == 'shared':
            service_def['provider'] = 'ArcObjectsRasterRendering'
            service_def['minInstancesPerNode'] = 0
            service_def['maxInstancesPerNode'] = 0
        elif instance_type == 'reserved':
            service_def['provider'] = 'ArcObjects'
            service_def['minInstancesPerNode'] = 1
            service_def['maxInstancesPerNode'] = 2
        arcgiscache_path, arcgiscache_virtual_path = self._get_directory_path(
            'arcgiscache',
            token,
            self._serverurl)
        arcgisoutput_path, arcgisoutput_virtual_path = self._get_directory_path(
            'arcgisoutput',
            token,
            self._serverurl)
        service_def['properties']['cacheDir'] = arcgiscache_path
        service_def['properties']['outputDir'] = arcgisoutput_path
        service_def['properties']['virtualCacheDir'] = arcgiscache_virtual_path
        service_def['properties']['virtualOutputDir'] = arcgisoutput_virtual_path
        if service_params:
            if not all(service_param_key in service_def['properties'] for service_param_key in service_params):
                return self._get_result_status(success=False,
                                               message="Error in the additional server definition parmaters passed. Please check if the parameters passed are valid.")
            for key in service_params:
                if key in service_def['properties']:
                    service_def['properties'][key] = service_params[key]
        json_param = {
            'f': 'json',
            'token': token,
            'service': json.dumps(service_def)
        }
        try:
            results = requests.post(create_service_url,
                                    json_param, verify=False)
            result_json = results.json()
            if result_json.get('status') == 'success':
                log.Message(
                    "Successfully created service " + service_name,
                    log.const_general_text)
                return self._get_result_status(success=True, message="")
            else:
                err_messages = ['Error in creating service.']
                err_messages.extend(result_json.get('messages'))
                err_message = ' '.join(err_messages)
                log.Message(err_message, log.const_critical_text)
                return self._get_result_status(success=False,
                                               message=err_message)
        except Exception as e:
            err_message = "".join([
                "Error in creating service ",
                service_name])
            log.Message(err_message, log.const_critical_text)
            return self._get_result_status(success=False, message=err_message)

    def _get_result_status(self, success, message, **kwargs):
        result_status = {"success": success, "message": message}
        result_status.update(kwargs)
        return result_status

    def _share_item(self, item_id, portalurl, username, token, public):
        share_url = "".join([portalurl,
                             "/sharing/rest/content/users/",
                             username, "/shareItems"])
        try:
            params = {
                'token': token,
                'f': 'json',
                'items': item_id,
                'everyone': public
            }
            result = requests.post(share_url, data=params, verify=False)
            result_json = result.json()
            if(result_json.get('results') and
               result_json.get('results')[0] and
               result_json.get('results')[0].get('success')):
                log.Message("Successfully shared portal item ",
                            log.const_general_text)
                return self._get_result_status(success=True, message="")
            else:
                error_message = ''.join([
                    'Error in share item. ',
                    result_json.get('error').get('message')])
                log.Message("Error in sharing portal item " + error_message,
                            log.const_critical_text)
                return self._get_result_status(success=False,
                                               message=error_message)
        except Exception as e:
            log.Message("Error in sharing portal item ",
                        log.const_critical_text)
            return self._get_result_status(
                success=False,
                message="Error in sharing portal item ")

    def close(self):
        log.Message("Done", log.const_general_text)
        log.WriteLog('#all')
#i = ImageryServices()
#i.get_all_server_folders()
#service_params = {'availableMensurationCapabilities': 'None,Basic,Base-Top Height,Top-Top Shadow Height,Base-Top Shadow Height,3D', 'allowedMensurationCapabilities': 'Basic', 'maxImageHeight': '4000', 'allowedMosaicMethods': 'ByAttribute;Seamline;NorthWest;Center;LockRaster;Nadir;None', 'availableFields': 'Name;MinPS;MaxPS;LowPS;HighPS;ProductName;CenterX;CenterY;SensorName;AcquisitionDate;SunAzimuth;SunElevation;CloudCover;Best;PR;Month;DayOfYear;WRS_Path;WRS_Row;Latest;DateUpdated;GroupName;dataset_id;Shape_Area;Shape_Length', 'defaultCompressionQuality': '85', 'availableCompressions': 'JPEG,NONE,LERC,LZ77', 'availableMosaicMethods': 'NorthWest,Center,LockRaster,ByAttribute,Nadir,Viewpoint,Seamline,None', 'allowedCompressions': 'JPEG,NONE,LERC,LZ77'}
#i.create_service('test', 'ss3', r'c:\temp\LandsatGLS.gdb\GLS_PS_4b16b', 'description', 'copyright', 
                #'md',# service_params=service_params, 
                #instance_type='shared')