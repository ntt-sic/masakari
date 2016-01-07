#!/bin/bash 

# Copyright(c) 2015 Nippon Telegraph and Telephone Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Define constants
SCRIPT_DIR="/opt/masakari/masakari-processmonitor"
SCRIPT_COMMON_SH="$SCRIPT_DIR/common.sh"

TMP_DIR="/var/tmp"
PROC_LIST=/etc/masakari/proc.list
BAD_CODE_LIST_FILE="$TMP_DIR/badproc.list"

# Common processing (check of proc.list)
. $SCRIPT_COMMON_SH
check_proc_file_common

# Get the process list.
ps_result=`ps -ef`

# Initialize abnormal condition list
cat /dev/null > ${BAD_CODE_LIST_FILE}

# Process check main processing
while read line
do
    PROC_NO=`echo $line | cut -d"," -f 1`
    PROC_NAME=`echo $line | cut -d"," -f 2`
    PROC_CHECK=`echo $ps_result |grep -c "${PROC_NAME}"`
    # If process was not detect, register ID in the abnormality process.
    if [ ${PROC_CHECK} -eq 0 ]; then
        log_info "down process id_no : ${PROC_NO}"
        echo ${PROC_NO} >> ${BAD_CODE_LIST_FILE}
    fi
done < ${PROC_LIST}

# If failing process ID was detected, decide state as abnormal termination(exit code:1).
if [ -s ${BAD_CODE_LIST_FILE} ]; then
    exit 1
fi

exit 0
