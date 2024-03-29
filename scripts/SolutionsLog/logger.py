# ------------------------------------------------------------------------------
# Copyright 2021 Esri
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
# Name: logger.py
# Description: Class to log status from Imagery w/f components to log files.
# Version: 20210711
# Requirements: Python
# Author: Esri Imagery Workflows team
# ------------------------------------------------------------------------------
# !/usr/bin/env python

from xml.dom.minidom import Document
from datetime import datetime

import os
import sys

homePath = os.path.dirname(os.path.dirname(__file__))
sys.path.append(homePath)
sys.path.append(os.path.join(homePath, 'Base'))
try:
    import Base
except:
    pass
const_start_time_node = 'StartTime'
const_end_time_node = 'EndTime'

class Logger(object):

    const_general_text = 0
    const_warning_text = 1
    const_critical_text = 2
    const_status_text = 3

    def __init__(self, base=None):
        self.projects = {}
        self.command_order = []
        self.active_key = ''
        self.logFolder = ''
        self.projectName = 'Project'  # default project name

        self.start_time = None
        self.end_time = None
        self.duration = None
        self.duration_label = ''
        self.logNamePrefix = ''
        self.logFileName = ''
        if (base):
            if (hasattr(base, 'setLog')):
                base.setLog(base.m_log)
        self.m_base = base
        self.isGPRun = False
        self.isPrint = True

    @property
    def LogNamePrefix(self):
        return self.logNamePrefix

    def LogNamePrefix(self, value):
        self.logNamePrefix = value

    def LogFileName(self, value):
        self.logFileName = value

    def Project(self, name):
        self.projectName = name

    def StartLog(self):
        if (self.start_time is None):  # project start time.
            self.start_time = datetime.now()

    def CloseCategory(self):
        if (const_start_time_node in self.projects[self.active_key].keys()):
            end_time = datetime.now()
            start_time = self.projects[self.active_key][const_start_time_node]
            duration = end_time - start_time
            self.projects[self.active_key]['EndTime'] = end_time
            self.projects[self.active_key]['DurationLabel'] = "%u" % (duration.total_seconds())

        self.SetCurrentCategory('')

    def EndLog(self):
        self.end_time = datetime.now()

        if (self.start_time is not None):
            self.duration = self.end_time - self.start_time

    def SetLogFolder(self, logFolder):
        self.logFolder = logFolder

    def SetCurrentCategory(self, category):
        if (category == ''):
            category = '__root'
        if ((category in self.projects.keys()) == False):
            self.CreateCategory(category)
        self.active_key = category

    def CreateCategory(self, project):
        key = project.strip()
        if ((key in self.projects.keys()) == False):
            self.projects[key] = {'logs': {'message': []}}
            self.active_key = key
            self.projects[key][const_start_time_node] = datetime.now()
            self.command_order.append(key)

    def Message(self, message, messageType):
        if (len(message) == 0):
            return False
        if (self.active_key == ''):
            self.SetCurrentCategory('')
        key = self.active_key
        errorTypeText = 'msg'
        if (messageType is None or
            messageType == self.const_general_text or
                messageType == self.const_status_text):
            if (messageType == self.const_status_text):
                errorTypeText = 'status'
            self.projects[key]['logs']['message'].append({'text': message, 'type': errorTypeText})
        elif(messageType > self.const_general_text):  # warning
            errorTypeText = 'warning'
            if (messageType == self.const_critical_text):
                errorTypeText = "critical"
            self.projects[key]['logs']['message'].append({'error': {'type': errorTypeText, 'text': message}})
        _message = 'log-{}:{}'.format(errorTypeText, message)  # print out error message to console while logging.
        if (self.isGPRun):
            try:
                import arcpy
                if (messageType == self.const_warning_text):
                    arcpy.AddWarning(_message)
                elif (messageType == self.const_critical_text):
                    arcpy.AddWarning(_message)      # arcpy.AddError causes a crash. For now, all critical errors are shown as warnings.
                else:
                    arcpy.AddMessage(_message)
            except:
                pass
        else:
            if (self.isPrint):          # via (self.isPrint) clients can disable the default printToConsole/print
                print (_message)        # if a client side msgCallback has been set.
            msg_type = 'general'        # msg-code
            if (self.m_base):
                if (hasattr(self.m_base, 'invoke_cli_msg_callback')):   # used by MDCS
                    self.m_base.invoke_cli_msg_callback(msg_type, [_message])
                elif(hasattr(self.m_base, 'writeToConsole')):  # used by OptimizeRasters
                    self.m_base.writeToConsole(_message)
        return True

    def WriteLog(self, project):
        const_startend_time_format = "%04d%02d%02dT%02d%02d%02d"
        prj = project.strip()
        key_command = prj
        doc = Document()
        eleDoc = doc.createElement('Projects')
        eleParent = doc.createElement(self.projectName)
        if (self.start_time is not None):
            startLogNode = doc.createElement(const_start_time_node)
            time_log_lebel = const_startend_time_format % (self.start_time.year, self.start_time.month, self.start_time.day,
                                                           self.start_time.hour, self.start_time.minute, self.start_time.second)
            startLogNode.appendChild(doc.createTextNode(time_log_lebel))
            eleParent.appendChild(startLogNode)
# add start-time, end-time and the duration under each project node.
            end_time = datetime.now()
            if (self.end_time is not None):
                end_time = self.end_time
            endLogNode = doc.createElement('EndTime')
            time_log_lebel = const_startend_time_format % (end_time.year, end_time.month, end_time.day,
                                                           end_time.hour, end_time.minute, end_time.second)
            endLogNode.appendChild(doc.createTextNode(time_log_lebel))
            eleParent.appendChild(endLogNode)
            durationLogNode = doc.createElement('TotalDuration')
            duration = end_time - self.start_time
            durationLogNode.appendChild(doc.createTextNode("%u" % (duration.total_seconds())))
            eleParent.appendChild(durationLogNode)
        eleDoc.appendChild(eleParent)
        doc.appendChild(eleDoc)
        for key_ in self.command_order:
            if (key_ == prj or key_command == '#all'):
                if (key_command == '#all'):
                    prj = key_
                if (key_ != '__root'):
                    eleProject = doc.createElement(prj)
                msgNode = None
                for key in self.projects[key_]:
                    if (key == 'logs'):
                        for msg in self.projects[prj]['logs']['message']:
                            if ('text' in msg.keys()):
                                nodeName = 'Message'
                                if (msg['type'] == 'status'):
                                    nodeName = 'Status'
                                eleMessage = doc.createElement(nodeName)
                                eleText = doc.createTextNode(str(msg['text']))
                                eleMessage.appendChild(eleText)
                                msgNode = eleMessage
                            elif('error' in msg.keys()):
                                eleError = doc.createElement('Error')
                                eleErrorType = doc.createElement('type')
                                eleErrorType.appendChild(doc.createTextNode(msg['error']['type']))
                                eleErrorText = doc.createElement('text')
                                eleErrorText.appendChild(doc.createTextNode(msg['error']['text']))
                                eleError.appendChild(eleErrorType)
                                eleError.appendChild(eleErrorText)
                                # if warning/error begins without a parent 'Message' node, create an empty 'Message' parent node.
                                if (msgNode is None):
                                    msgNode = doc.createElement('Message')
                                    eleMessage = msgNode
                                msgNode.appendChild(eleError)
                            if (key_ == '__root'):
                                eleParent.appendChild(eleMessage)
                            else:
                                eleProject.appendChild(eleMessage)
                        if ('DurationLabel' in self.projects[prj].keys()):
                            durationLogNode = doc.createElement('Duration')
                            durationLogNode.appendChild(doc.createTextNode(self.projects[prj]['DurationLabel']))
                            if (key_ == '__root'):
                                eleParent.appendChild(durationLogNode)
                            else:
                                eleProject.appendChild(durationLogNode)
                        if (key_ != '__root'):
                            eleParent.appendChild(eleProject)
                        eleDoc.appendChild(eleParent)
        try:

            # log reports can be saved uniquely named with date and time for easy review.
            ousr_date = datetime.now()
            prefix = self.logNamePrefix
            if(prefix == ''):
                prefix = 'log'
            recordUpdated = prefix + "_%04d%02d%02dT%02d%02d%02d.xml" % (ousr_date.year, ousr_date.month, ousr_date.day,
                                                                         ousr_date.hour, ousr_date.minute, ousr_date.second)

            if (self.logFileName.strip() != ''):
                recordUpdated = self.logFileName
                if (recordUpdated[-4:].lower() != '.xml'):
                    recordUpdated += '.xml'
            # try to create the log-folder if not found!
            if (os.path.exists(self.logFolder) == False):
                os.mkdir(self.logFolder)
            logPath = os.path.join(self.logFolder, recordUpdated)
            c = open(logPath, "w")
            c.write(doc.toprettyxml())
            c.close()
        except:
            print ("\nError creating log file.")
