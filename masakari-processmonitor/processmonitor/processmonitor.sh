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

# Define constants.
BASE_NAME=`basename $0`
TMP_DIR="/var/tmp"
TMP_CRM_MON_FILE="$TMP_DIR/crm_mon.tmp"
STATUS_FILE="$TMP_DIR/node_status.tmp"
TMP_CRMADM_FILE="$TMP_DIR/crmadmin.tmp"
NOTICE_OUTPUT="$TMP_DIR/${BASE_NAME}_resp.out"
JSON_DIR="$TMP_DIR/tmp_json_files"

SCRIPT_DIR="/opt/processmonitor"
SCRIPT_CONF_FILE="/etc/processmonitor/processmonitor.conf"
SCRIPT_CHECK_PROCESS="$SCRIPT_DIR/process_status_checker.sh"
SCRIPT_COMMON_SH="$SCRIPT_DIR/common.sh"

#DOWN_PROCESS_LIST="$SCRIPT_DIR/badproc.list"
#PROC_LIST="$SCRIPT_DIR/proc.list"
DOWN_PROCESS_LIST="/etc/processmonitor/badproc.list"
PROC_LIST="/etc/processmonitor/proc.list"

RESOURCE_MANAGER_SEND_PROGRAM=curl
RESOURCE_MANAGER_SEND_FAIL_FLG="off"

ALREADY_SEND_ID_LIST=()
LOGTAG=`basename $0`

# Define the default setting.
DEFAULT_PROCESS_CHECK_INTERVAL=5
DEFAULT_PROCESS_REBOOT_RETRY=3
DEFAULT_REBOOT_INTERVAL=10
DEFAULT_RESOURCE_MANAGER_SEND_TIMEOUT=10
DEFAULT_RESOURCE_MANAGER_SEND_RETRY=12
DEFAULT_RESOURCE_MANAGER_SEND_DELAY=10
DEFAULT_RESOURCE_MANAGER_SEND_RETRY_TIMEOUT=120


# This function locks a file
# Argument:
#   $1 : File name
file_lock () {
    exec 9>>$1
    flock -x 9
}

# This function unlocks a file
file_unlock () {
    exec 9>&-
}

# This function reads the configuration file and setting value.
# If the value is omitted, set the default value.
# If invalid value is set, return "1".
# Note) The default value for each item are as follows.
#       PROCESS_CHECK_INTERVAL (defualt : 60)
#       PROCESS_REBOOT_RETRY (default : 10)
#       REBOOT_INTERVAL (default : 3)
#       RESOURCE_MANAGER_SEND_TIMEOUT (defualt : 10)
#       RESOURCE_MANAGER_SEND_RETRY (default : 3)
#       RESOURCE_MANAGER_SEND_DELAY (default : 1)
#       RESOURCE_MANAGER_SEND_RETRY_TIMEOUT (default : 10)
#
# Return value:
#   0 : Setting completion
#   1 : Reading failure of the configuration or invalid setting value
#   2 : Omission of the required item
set_conf_value () {
    # Initialize setting
    unset RESOURCE_MANAGER_URL
    unset PROCESS_CHECK_INTERVAL
    unset PROCESS_REBOOT_RETRY
    unset REBOOT_INTERVAL
    unset RESOURCE_MANAGER_SEND_TIMEOUT
    unset RESOURCE_MANAGER_SEND_RETRY
    unset RESOURCE_MANAGER_SEND_RETRY_TIMEOUT
    unset RESOURCE_MANAGER_SEND_DELAY
    unset REGION_ID

    # Read configuration file
    source $SCRIPT_CONF_FILE > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        log_info "config file read error. [$SCRIPT_CONF_FILE]"
        return 1
    fi

    # Empty string is permitted. If there is no key itself, consider it as an error.
    if [ "${RESOURCE_MANAGER_URL-UNDEF}" = "UNDEF" ]; then
        log_info "config file parameter not found. [$SCRIPT_CONF_FILE:RESOURCE_MANAGER_URL]"
        return 2
    fi
    log_debug "config file parameter : RESOURCE_MANAGER_URL=$RESOURCE_MANAGER_URL"

    # If the PROCESS_CHECK_INTERVAL is omitted, set the default value.
    # If invalid is set, return 1.
    expect_empty=`echo -n $PROCESS_CHECK_INTERVAL | sed 's/[0-9]//g'`
    if [ "x" = "x${PROCESS_CHECK_INTERVAL}" ]; then
        PROCESS_CHECK_INTERVAL=$DEFAULT_PROCESS_CHECK_INTERVAL
    elif [ "x" != "x${expect_empty}" ]; then
        log_info "config file parameter error. [$SCRIPT_CONF_FILE:PROCESS_CHECK_INTERVAL]"
        return 1
    fi
    log_debug "config file parameter : PROCESS_CHECK_INTERVAL=$PROCESS_CHECK_INTERVAL"

    # If the PROCESS_REBOOT_RETRY is omitted, set the default value.
    # If invalid is set, return 1.
    expect_empty=`echo -n $PROCESS_REBOOT_RETRY | sed 's/[0-9]//g'`
    if [ "x" = "x${PROCESS_REBOOT_RETRY}" ]; then
        PROCESS_REBOOT_RETRY=$DEFAULT_PROCESS_REBOOT_RETRY
    elif [ "x" != "x${expect_empty}" ]; then
        log_info "config file parameter error. [$SCRIPT_CONF_FILE:PROCESS_REBOOT_RETRY]"
        return 1
    fi
    log_debug "config file parameter : PROCESS_REBOOT_RETRY=$PROCESS_REBOOT_RETRY"

    # If the REBOOT_INTERVAL is omitted, set the default value.
    # If invalid is set, return 1.
    expect_empty=`echo -n $REBOOT_INTERVAL | sed 's/[0-9]//g'`
    if [ "x" = "x${REBOOT_INTERVAL}" ]; then
        REBOOT_INTERVAL=$DEFAULT_REBOOT_INTERVAL
    elif [ "x" != "x${expect_empty}" ]; then
        log_info "config file parameter error. [$SCRIPT_CONF_FILE:REBOOT_INTERVAL]"
        return 1
    fi
    log_debug "config file parameter : REBOOT_INTERVAL=$REBOOT_INTERVAL"

    # If the RESOURCE_MANAGER_SEND_TIMEOUT is omitted, set the default value.
    # If invalid is set, return 1.
    expect_empty=`echo -n $RESOURCE_MANAGER_SEND_TIMEOUT | sed 's/[0-9]//g'`
    if [ "x" = "x${RESOURCE_MANAGER_SEND_TIMEOUT}" ]; then
        RESOURCE_MANAGER_SEND_TIMEOUT=$DEFAULT_RESOURCE_MANAGER_SEND_TIMEOUT
    elif [ "x" != "x${expect_empty}" ]; then
        log_info "config file parameter error. [$SCRIPT_CONF_FILE:RESOURCE_MANAGER_SEND_TIMEOUT]"
        return 1
    fi
    log_debug "config file parameter : RESOURCE_MANAGER_SEND_TIMEOUT=$RESOURCE_MANAGER_SEND_TIMEOUT"

    # If the RESOURCE_MANAGER_SEND_RETRY is omitted, set the default value.
    # If invalid is set, return 1.
    expect_empty=`echo -n $RESOURCE_MANAGER_SEND_RETRY | sed 's/[0-9]//g'`
    if [ "x" = "x${RESOURCE_MANAGER_SEND_RETRY}" ]; then
        RESOURCE_MANAGER_SEND_RETRY=$DEFAULT_RESOURCE_MANAGER_SEND_RETRY
    elif [ "x" != "x${expect_empty}" ]; then
        log_info "config file parameter error. [$SCRIPT_CONF_FILE:RESOURCE_MANAGER_SEND_RETRY]"
        return 1
    fi
    log_debug "config file parameter : RESOURCE_MANAGER_SEND_RETRY=$RESOURCE_MANAGER_SEND_RETRY"

    # If the RESOURCE_MANAGER_SEND_RETRY_TIMEOUT is omitted, set the default value.
    # If invalid is set, return 1.
    expect_empty=`echo -n $RESOURCE_MANAGER_SEND_RETRY_TIMEOUT | sed 's/[0-9]//g'`
    if [ "x" = "x${RESOURCE_MANAGER_SEND_RETRY_TIMEOUT}" ]; then
        RESOURCE_MANAGER_SEND_RETRY_TIMEOUT=$DEFAULT_RESOURCE_MANAGER_SEND_RETRY_TIMEOUT
    elif [ "x" != "x${expect_empty}" ]; then
        log_info "config file parameter error. [$SCRIPT_CONF_FILE:RESOURCE_MANAGER_SEND_RETRY_TIMEOUT]"
        return 1
    fi
    log_debug "config file parameter : RESOURCE_MANAGER_SEND_RETRY_TIMEOUT=$RESOURCE_MANAGER_SEND_RETRY_TIMEOUT"

    # If the RESOURCE_MANAGER_SEND_DELAY is omitted, set the default value.
    # If invalid is set, return 1.
    expect_empty=`echo -n $RESOURCE_MANAGER_SEND_DELAY | sed 's/[0-9]//g'`
    if [ "x" = "x${RESOURCE_MANAGER_SEND_DELAY}" ]; then
        RESOURCE_MANAGER_SEND_DELAY=$DEFAULT_RESOURCE_MANAGER_SEND_DELAY
    elif [ "x" != "x${expect_empty}" ]; then
        log_info "config file parameter error. [$SCRIPT_CONF_FILE:RESOURCE_MANAGER_SEND_DELAY]"
        return 1
    fi
    log_debug "config file parameter : RESOURCE_MANAGER_SEND_DELAY=$RESOURCE_MANAGER_SEND_DELAY"

    # If the REGION_ID is omitted, return 1.
    if [ -z "$REGION_ID" ]; then
        log_info "config file parameter error. [$SCRIPT_CONF_FILE:REGION_ID]"
        return 2
    fi
    log_debug "config file parameter : REGION_ID=$REGION_ID"

    return 0
}

# Initial startup command execution method:
# This method does not execute same command as startup command that executed once.

init_boot() {
    log_debug "init_boot start"
    CMD_LIST=()
    for line in "${proc_list[@]}"
    do
        ALREADY_FLG="off"
        CMD=`echo ${line} | cut -d"," -f 3`
        SPECIAL_BEFORE=`echo $line | cut -d"," -f 5`
        SPECIAL_AFTER=`echo $line | cut -d"," -f 6`

        # If there is no startup command, can proceed to the next command.
        if [ -z "$CMD" ]; then
            continue
        fi
 
        # Check whether already is executed.
        for CHECK_CMD in "${CMD_LIST[@]}"
        do
            if [ "$CHECK_CMD" = "$CMD" ]; then
                ALREADY_FLG="on"
                break
            fi
        done

        # Execute special processing before the initial startup.
        if [ ! -z "$SPECIAL_BEFORE" ]; then
            $SPECIAL_BEFORE
        fi

        # If not be executed, execute start command.
        if [ "$ALREADY_FLG" = "off" ]; then
            OLD_IFS=$IFS
            IFS=';'
            set -- $CMD
            CMD_SPLIT_LIST=("$@")
            IFS=$OLD_IFS
            for SPLIT_CMD in "${CMD_SPLIT_LIST[@]}"
            do
                $SPLIT_CMD > /dev/null 2>&1 
            done

            CMD_LIST=("$CMD_LIST" "$CMD")
        fi

        # Execute special processing after the initial startup.
        if [ ! -z "$SPECIAL_AFTER" ]; then
            $SPECIAL_AFTER
        fi
    done
    log_debug "init_boot end"
}

# This function creates data that is notified to the resource management.
# It is called from the child process.
#
make_notice_data () {
    ID=`uuidgen`
    TYPE="nodeStatus"

    L_HOST=`uname -n`
    P_HOST=$L_HOST

    EVENT_ID="1"
    EVENT_TYPE="1"
    DETAIL=$1
    START_TIME=`date +'%Y%m%d%H%M%S'`
    TIME="${START_TIME}"

    get_tzname_daylight

    echo "{"
    cat <<NOTICE_DATA_END
    "id": "${ID}",
    "type": "${TYPE}",
    "regionID": "${REGION_ID}",
    "hostname": "${P_HOST}",
    "uuid": "",
    "time": "${TIME}",
    "eventID": "${EVENT_ID}",
    "eventType": "${EVENT_TYPE}",
    "detail": "${DETAIL}",
    "startTime": "${START_TIME}",
    "endTime": null,
    "tzname": "${TZ_NAME}",
    "daylight": "${DAYLIGHT}",
    "cluster_port": ""
NOTICE_DATA_END
    echo "}"
}

# This function gets timezone and the daylight saving time, set time to varlable
get_tzname_daylight () {
    # Get timezone.
    TZ_NAME=`python -c "import time
print time.tzname"`
    TZ_NAME=`echo "$TZ_NAME" | cut -d"(" -f2 | cut -d")" -f1`

    # Get the daylight time.
    DAYLIGHT=`python -c "import time
print time.daylight"`
}

# This function notifies to the resource management.
# It is called from child process.
#
# Arguments:
#   $1 : Json file name
# Return value:
#   0 : Notification is sucessful.
#   1 : Notification is failed.
send_to_rm () {
    log_debug "info : send_to_rm : begin"

    if [ -z $RESOURCE_MANAGER_URL ]; then
        log_info "info : RM server URL is not set."
        log_info "info : $BASE_NAME : end"
        return 0
    fi
    # Create required information to execute.
    NOTICE_OPTS="--silent"
    NOTICE_OPTS+=" --header \"Content-Type:application/json\""
    NOTICE_OPTS+=" --write-out \"HTTP_CODE=%{response_code}\n\""
    NOTICE_OPTS+=" --max-time ${RESOURCE_MANAGER_SEND_TIMEOUT}"
    NOTICE_OPTS+=" --retry ${RESOURCE_MANAGER_SEND_RETRY}"
    NOTICE_OPTS+=" --retry-max-time ${RESOURCE_MANAGER_SEND_RETRY_TIMEOUT}"
    NOTICE_OPTS+=" --retry-delay ${RESOURCE_MANAGER_SEND_DELAY}"
    NOTICE_OPTS+=" --data @$1"
    log_info "info : $RESOURCE_MANAGER_SEND_PROGRAM $NOTICE_OPTS $RESOURCE_MANAGER_URL"
    log_info "info : data : `cat $1`"

    # The body of the resource management notification processing
    retry_count=1
    while [ ${retry_count} -le ${RESOURCE_MANAGER_SEND_RETRY} ]
    do
        $RESOURCE_MANAGER_SEND_PROGRAM $NOTICE_OPTS $RESOURCE_MANAGER_URL >$NOTICE_OUTPUT
        result=$?
        if [ $result -eq 7 ]; then
            log_debug "info : $RESOURCE_MANAGER_SEND_PROGRAM fail. Connection refused.(${retry_count}) [exit-code: $result]"
            sleep ${RESOURCE_MANAGER_SEND_DELAY}
            retry_count=`expr ${retry_count} + 1`
            continue
        elif [ $result -ne 0 ]; then
            log_info "info : $RESOURCE_MANAGER_SEND_PROGRAM fail. [exit-code: $result]"
            log_info "info : $BASE_NAME : end"
            RESOURCE_MANAGER_SEND_FAIL_FLG="on"
            return 1
        else
            HTTP_STATUS_CODE="`grep HTTP_CODE $NOTICE_OUTPUT | tail -1 | sed 's/'.*HTTP_CODE='//g'`"
            log_info "info : Notice response. [status-code: $HTTP_STATUS_CODE]"
            break
        fi
    done

    if [ ${retry_count} -gt ${RESOURCE_MANAGER_SEND_RETRY} ]; then
        log_info "$1 info : $RESOURCE_MANAGER_SEND_PROGRAM fail. Connection refused.(Tried 'curl' ${RESOURCE_MANAGER_SEND_RETRY} times.) [exit-code: $result]"
        log_debug "info : send_to_rm : end"
        return 1
    else
        log_debug "info : send_to_rm : end"
        return 0
    fi
}


# Attempt to restart the failer process.
# If failure to number of retries, notify to the resource management.
 
down_process_reboot(){
    ALREADY_REBOOT_CMD_LIST=()
    while read line
    do
        ALREADY_FLG="off"
        # No processing is executed about process id included in the send list.
        for already_id in "${ALREADY_SEND_ID_LIST[@]}"
        do
            if [ "$line" = "$already_id" ]; then
                ALREADY_FLG="on"
                break
            fi
        done

        if [ "$ALREADY_FLG" = "on" ]; then
            continue
        fi

        for proc in "${proc_list[@]}"
        do
            PROC_ID=`echo $proc | cut -d"," -f 1`
            if [ "$line" = "$PROC_ID" ] ; then
                CMD=`echo $proc | cut -d"," -f 4`
                SPECIAL_BEFORE=`echo $proc | cut -d"," -f 7`
                SPECIAL_AFTER=`echo $proc | cut -d"," -f 8`
                break
            fi
        done

        if [ ! -z "$SPECIAL_BEFORE" ]; then
            $SPECIAL_BEFORE
        fi

        # If there is not restart command, can proceed to the next command.
        if [ -z "$CMD" ]; then
            continue
        fi

        RESULT_FLG=1
        # Decomposes multiple processing be joined by ";" and execute them. (restart execution part)
        OLD_IFS=$IFS
        IFS=';'
        set -- $CMD
        CMD_SPLIT_LIST=("$@")
        IFS=$OLD_IFS
        for SPLIT_CMD in "${CMD_SPLIT_LIST[@]}"
        do
            ALREADY_FLG="off" 
            # Check whether already is executed.
            for CHECK_CMD in "${ALREADY_REBOOT_CMD_LIST[@]}"
            do
                if [ "$CHECK_CMD" = "$SPLIT_CMD" ]; then
                    ALREADY_FLG="on"
                    break
                fi
            done
            # If is already executed, skip.
            if [ "$ALREADY_FLG" = "on" ]; then
                continue
            fi
            
            log_debug "reboot cmd:$SPLIT_CMD"
            $SPLIT_CMD > /dev/null 2>&1
            if [ $? -ne 0 ]; then
                RESULT_FLG=0
                break
            else
                ALREADY_REBOOT_CMD_LIST=("$ALREADY_REBOOT_CMD_LIST" "$SPLIT_CMD")
            fi
        done

        # If fail to restart, executes retry restart.
        if [ $RESULT_FLG -ne 1 ]; then
            for retry in `seq $PROCESS_REBOOT_RETRY`
            do
                sleep $REBOOT_INTERVAL
                # Retry the restart processing.
                RESULT_FLG=1
                for SPLIT_CMD in "${CMD_SPLIT_LIST[@]}"
                do
                    ALREADY_FLG="off"
                    # Check whether already is executed.
                    for CHECK_CMD in "${ALREADY_REBOOT_CMD_LIST[@]}"
                    do
                        if [ "$CHECK_CMD" = "$SPLIT_CMD" ]; then
                            ALREADY_FLG="on"
                            break
                        fi
                    done
                    # If is already executed, skip.
                    if [ "$ALREADY_FLG" = "on" ]; then
                        continue
                    fi
                    log_debug "reboot cmd:$SPLIT_CMD"
                    $SPLIT_CMD > /dev/null 2>&1
                    if [ $? -ne 0 ]; then
                        RESULT_FLG=0
                        break
                    else
                        ALREADY_REBOOT_CMD_LIST=("$ALREADY_REBOOT_CMD_LIST" "$SPLIT_CMD")
                    fi
                done
                if [ $RESULT_FLG -eq 1 ]; then
                    break
                elif [ $retry -eq $PROCESS_REBOOT_RETRY ]; then
                    # If number of retries is exceeded, notify to the resource management.
                    mkdir -p $JSON_DIR
                    JSON_FILE="${JSON_DIR}/${BASE_NAME}.json"
                    make_notice_data ${line} > $JSON_FILE
                    if [ "$RESOURCE_MANAGER_SEND_FAIL_FLG" = "off" ]; then
                        send_to_rm $JSON_FILE
                    fi
                    # Add the sent list.
                    ALREADY_SEND_ID_LIST=("${ALREADY_SEND_ID_LIST[@]}" "${line}")
                fi
            done
        fi

        # Special processes after restart.
        if [ ! -z "$SPECIAL_AFTER" ]; then
            $SPECIAL_AFTER
        fi


    done < $DOWN_PROCESS_LIST
}



# Initial processing (check proc.list and read conf file)
. $SCRIPT_COMMON_SH 
log_debug "processmonitor start!!"
check_proc_file_common
set_conf_value
if [ $? -ne 0 ]; then
    exit 1
fi

if [ -e $NOTICE_OUTPUT ]; then
    sudo rm -rf $NOTICE_OUTPUT
fi
if [ -e $JSON_DIR ]; then
    sudo rm -rf $JSON_DIR
fi

# Initial startup
init_boot

while true
do
    # Recheck and reload of the proc.list.
    check_proc_file_common
    # If invalid value is set to configuration file, set default value.
    set_conf_value

    if [ $? -eq 2 ]; then
       exit 1
    fi

    # Execute process check processing.
    ${SCRIPT_CHECK_PROCESS}
    RESULT_CODE=$?

    # If the return code is 2, because can't continue functionally, stop.
    if [ $RESULT_CODE -eq 2 ]; then
        log_debug "process_status_checker down!"
        exit 1
    fi
    
    # If the failing process is detected by shell check, retry restart.
    if [ $RESULT_CODE -ne 0 ]; then
        down_process_reboot
    fi

    sleep ${PROCESS_CHECK_INTERVAL}
done

