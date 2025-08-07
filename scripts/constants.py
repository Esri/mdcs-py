"""-----------------------------------------------------------------------------
Copyright 2025 Esri
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
------------------------------------------------------------------------------
Name: constants.py
Description: Holds global vars that can be shared across MDCS modules.
Version: 20250611
Requirements: Calling source file.
Usage: from constants import *
Author: Esri Imagery Workflows Team
---------------------------------------------------------------------------"""

WF_STATUS_TBL = "wfStatus.db"  # Session based MDCS storage
RT_INIT = 0  # rt init, * rt == (real-time)
RT_INF = 1  # rt general msg
RT_WF_END = 2  # rt mark the end of w/f
RT_CUR_CMD = 4  # rt currently executing MDCS command update.
RT_PMO = 6  # rt performance metrics
RT_SESSION_CLEANUP = 5
RT_UPD_PROG_TBL = 1000
RT_INTERVAL = 60
MSG_INF = 0  # regular text
MSG_WRN = 1  # warning
MSG_ERR = 2  # error
MSG_STS = 3  # MDCS command return status
RD_QUEUE_NAME = "mdcs_streamer"
RD_CHANNEL = "mdcs"
RD_HOST = "127.0.0.1"  # redis host
RD_PORT = 6379  # redis port
DELAY_BF_REREQUEST = 2
DELAY_POLL_SRV = 5
MAX_CLI_REC = 100  # Codes relevant to MDCS sever # 11 {
EC_ACCEPTED = 1
EC_WF_FINISHED = 2
EC_IN_QUEUE = -1
EC_MAX_LIMIT = -2
EC_CLOSED_CANCELLED = -3
EC_JOBID_MISSING = -4
EC_BUSY_EMPTY = -5
EC_MISSING_KEY = -6
EC_INVALID_REQ = -7
EC_CANCELLED_IN_LIMBO = -8
EC_FUTURE_JOB_CANCEL = -9
ESRI_JOB_CANCELLED = 100
SOC_BACKLOG = MAX_CLI_REC * 3  # 11 }
PERC_MAX = 100
PROC_EXITCODE_BASE = -100
MAX_SIGSEG_RETRY = 4
UC_CMD_TYPE_EVENT = 1
UC_CMD_TYPE_USER = 0
UC_CMD_TYPE_UNKNOWN = -1
MAX_SRV_RETRY_CNT = 7
