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

LOGTAG=`basename $0`
HOST_NAME=`hostname`
LOGDIR="/var/log/processmonitor"
LOGFILE="${LOGDIR}/processmonitor.log"

# Debug log output function
# Argument
#   $1 : Message
log_debug () {
    if [ ! -e ${LOGDIR} ]; then
        mkdir -p ${LOGDIR}
    fi

    if [ "${LOG_LEVEL}" == "debug" ]; then
        log_output "$1"
    fi
}

# Info log output function
# Argument
#   $1 : Message
log_info () {
    if [ ! -e ${LOGDIR} ]; then
        mkdir -p ${LOGDIR}
    fi

    log_output "$1"
}

# This function outputs the log
# Argument
#   $1 : Message
log_output () {
    echo "`date +'%Y-%m-%d %H:%M:%S'` ${HOST_NAME} ${LOGTAG}:  $1"  >> $LOGFILE
}

# Some sanity checks on the check target processing list.
# Format of the proc.list(Each columns must be separated by a comma.)
# The first column : Process ID (two digits of leading zeros) : cannot be omitted.
# The second column : The keyword when check exists in processing list(empty is NG.). : cannot be omitted
# The third column : The initial startup command (it's required to include word of "start". )
# The fourth column : Rebooting command (it's required to include word of "start".)
# The fifth column : Shell file name for special processing at the initial startup(before the startup)
# The sixth column : Shell file name for special processing at the initial startup(after the startup)
# The seventh column : Shell file name for special processing at the initial restart(before the startup)
# The eighth column : Shell file name for special processing at the initial restart(after the startup)
#
# When abonormal condition is detected about proc.list, exits by "exit 2".
column_num=8
check_proc_file_common (){

    # Check the existence and validity of the proc.list.
    if [ ! -e $PROC_LIST ]; then
        log_info "$PROC_LIST(proc_list) is not exists."
        exit 2
    fi

    if [ ! -s $PROC_LIST ]; then
        log_info "$PROC_LIST(proc_list) is empty file."
        exit 2
    fi

    if [ ! -r "$PROC_LIST" ]; then
        log_info "$PROC_LIST(proc_list) is not readable."
        exit 2
    fi

    OLD_IFS=$IFS
    IFS=$'\n'
    proc_list=(`cat $PROC_LIST`)
    IFS=$OLD_IFS

    LINE_NO=1

    for line in "${proc_list[@]}"
    do
        num=`echo "$line" | tr -dc ',' | wc -c`
        # The number of required column are incomplete.
        check_num=`expr $column_num - 1`
        if [ $num -ne $check_num ]; then
            log_info "$PROC_LIST format error (column_num) line $LINE_NO"
            exit 2
        fi

        PROC_ID=`echo $line | cut -d"," -f 1`
        if [ ! -z "$PROC_ID" ]; then
            expr "$PROC_ID" + 1  >/dev/null 2>&1
            # If PROC ID is not a numeric,
            if [ 1 -lt $? ]; then
                log_info "$PROC_LIST format error (PROC_ID) not number. line $LINE_NO"
                exit 2
            fi
        else
            log_info "$PROC_LIST format error (PROC_ID) empty. line $LINE_NO"
            exit 2
        fi

        KEY_WORD=`echo $line | cut -d"," -f 2`
        if [ -z "$KEY_WORD" ]; then
            log_info "$PROC_LIST format error (KEY_WORD) empty. line $LINE_NO"
            exit 2
        fi


        START_CMD=`echo $line | cut -d"," -f 3`
        if [ ! -z "$START_CMD" ]; then
            check=`echo $START_CMD | grep -c start`
            # If words of "start" are not included in initial startup processing.,
            if [ $check -ne 1 ]; then
                log_info "$PROC_LIST format error (START_CMD) line $LINE_NO"
                exit 2
            fi
        fi

        RESTART_CMD=`echo $line | cut -d"," -f 4`
        if [ ! -z "$RESTART_CMD" ]; then
            check=`echo $RESTART_CMD | grep -c start`
            # If words of "start" are not included in restart processing,
            if [ $check -ne 1 ]; then
                log_info "$PROC_LIST format error (RESTART_CMD) line $LINE_NO"
                exit 2
            fi
        fi

        # Check the existence and validity of special processing shell file to be executed before and after start processing.
        START_SP_CMDFILE_BEFORE=`echo $line | cut -d"," -f 5`
        if [ ! -z "$START_SP_CMDFILE_BEFORE" ]; then
            # The starting (before executing) special processing shell file does not exist.
            if [ ! -e $START_SP_CMDFILE_BEFORE ]; then
                log_info "$PROC_LIST format error (START_SP_CMDFILE_BEFORE) not exists. line $LINE_NO"
                exit 2
            fi
            if [ ! -x $START_SP_CMDFILE_BEFORE ]; then
                log_info "$PROC_LIST format error (START_SP_CMDFILE_BEFORE) not exeutable. line $LINE_NO"
                exit 2
            fi
        fi

        START_SP_CMDFILE_AFTER=`echo $line | cut -d"," -f 6`
        if [ ! -z "$START_SP_CMDFILE_AFTER" ]; then
            # The restarting (before executing) special processing shell file does not exist.
            if [ ! -e $START_SP_CMDFILE_AFTER ]; then
                log_info "$PROC_LIST format error (START_SP_CMDFILE_AFTER) not exists. line $LINE_NO"
                exit 2
            fi
            if [ ! -x $START_SP_CMDFILE_AFTER ]; then
                log_info "$PROC_LIST format error (START_SP_CMDFILE_AFTER) not exeutable. line $LINE_NO"
                exit 2
            fi
        fi

        # Check the existence and validity of special processing shell file to be executed before and after restart processing.
        RESTART_SP_CMDFILE_BEFORE=`echo $line | cut -d"," -f 7`
        if [ ! -z "$RESTART_SP_CMDFILE_BEFORE" ]; then
            # The restarting (before executing) special processing shell file does not exist.
            if [ ! -e $RESTART_SP_CMDFILE_BEFORE ]; then
                log_info "$PROC_LIST format error (RESTART_SP_CMDFILE_BEFORE) not exists. line $LINE_NO"
                exit 2
            fi
            if [ ! -x $RESTART_SP_CMDFILE_BEFORE ]; then
                log_info "$PROC_LIST format error (RESTART_SP_CMDFILE_BEFORE) not exeutable. line $LINE_NO"
                exit 2
            fi
        fi

        RESTART_SP_CMDFILE_AFTER=`echo $line | cut -d"," -f 8`
        if [ ! -z "$RESTART_SP_CMDFILE_AFTER" ]; then
            # The restarting (before executing) special processing shell file does not exist.
            if [ ! -e $RESTART_SP_CMDFILE_AFTER ]; then
                log_info "$PROC_LIST format error (RESTART_SP_CMDFILE_AFTER) not exists. line $LINE_NO"
                exit 2
            fi
            if [ ! -x $RESTART_SP_CMDFILE_AFTER ]; then
                log_info "$PROC_LIST format error (RESTART_SP_CMDFILE_AFTER) not exeutable. line $LINE_NO"
                exit 2
            fi
        fi

        LINE_NO=`expr $LINE_NO + 1`
     done
}

