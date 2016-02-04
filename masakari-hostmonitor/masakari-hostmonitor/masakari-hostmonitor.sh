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

# Define variables.
BASE_NAME=`basename $0`
TYPE="rscGroup"
HOST_NAME=`hostname`
MY_NODE_NAME=${HOST_NAME,,}
EVENT_ID="1"
DETAIL="1"
LOGTAG=`basename $0`
TMP_DIR="/var/tmp"
TMP_CRM_MON_FILE="$TMP_DIR/crm_mon.tmp"
STATUS_FILE="$TMP_DIR/node_status.tmp"
TMP_CRMADM_FILE="$TMP_DIR/crmadmin.tmp"
TMP_IFCONFIG_FILE="$TMP_DIR/ifconfig.tmp"
NOTICE_OUTPUT="$TMP_DIR/${BASE_NAME}_resp.out"
JSON_DIR="$TMP_DIR/tmp_json_files"
NOTICE_PROGRAM="curl"
SCRIPT_DIR="/opt/opencloud/hostmonitor"
SCRIPT_CONF_FILE="/etc/masakari/masakari-hostmonitor.conf"
RA_COUNT=0
HA_CONF="/etc/corosync/corosync.conf"
LOGDIR="/var/log/masakari"
LOGFILE="${LOGDIR}/masakari-hostmonitor.log"

# Define the node state.
NODE_STATUS_STARTED="Started"
NODE_STATUS_STOPPED="Stopped"
NODE_STATUS_STARTING="Starting"
NODE_STATUS_STOPPING="Stopping"
NODE_STATUS_UNKNOWN="Unknown"

# This function outputs the debug log
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

# This function outputs the info log
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

# This function locks a file
# Argument 
#   $1 : Message
file_lock () {
    exec 9>>$1
    flock -x 9
}

# This function unlocks a file
file_unlock () {
    exec 9>&-
}

# Initialization function
script_initialize () {
    ID=`uuidgen`
    log_debug "begin loop ID:$ID"
    if [ -f $TMP_CRM_MON_FILE ]; then
        sudo rm -f $TMP_CRM_MON_FILE
    fi
    if [ -f $NOTICE_OUTPUT ]; then
        sudo rm -f $NOTICE_OUTPUT
    fi
    if [ -e $JSON_DIR ]; then
        sudo rm -rf $JSON_DIR
    fi
    if [ -e $TMP_CRMADM_FILE ]; then
        sudo rm -rf $TMP_CRMADM_FILE
    fi
    if [ -e $TMP_IFCONFIG_FILE ]; then
        sudo rm -rf $TMP_IFCONFIG_FILE
    fi
    return 0
}

# Finalization function
# Argument
#  $1 : The flag indicating whether delete the node state file.
#        0 -> The node state file is deleted.
#        1 -> The node state file is not deleted.
script_finalize () {
    if [ $1 -eq 0 ]; then
        if [ -f $STATUS_FILE ]; then
            sudo rm -f $STATUS_FILE
        fi
    fi
    if [ -f $TMP_CRM_MON_FILE ]; then
        sudo rm -f $TMP_CRM_MON_FILE
    fi
    if [ -f $NOTICE_OUTPUT ]; then
        sudo rm -f $NOTICE_OUTPUT
    fi
    if [ -e $JSON_DIR ]; then
        sudo rm -rf $JSON_DIR
    fi
    if [ -e $TMP_CRMADM_FILE ]; then
        sudo rm -rf $TMP_CRMADM_FILE
    fi
    if [ -e $TMP_IFCONFIG_FILE ]; then
        sudo rm -rf $TMP_IFCONFIG_FILE
    fi
    log_debug "end loop ID:$ID"
    return 0
}

# Check the value is correct type
# Argument
#   $1: Type
#   $2: Parameter Name
#   $3: Value
# Return
#   0: The value is correct type
#   1: The value is not correct type
check_config_type() {
    expected_type=$1
    parameter_name=$2
    value=$3

    ret=0
    case $expected_type in
        int)
            expr $value + 1 > /dev/null 2>&1
            if [ $? -ge 2 ]; then ret=1; fi
            ;;
        string)
            if [ -z $value ] ; then ret=1; fi
            ;;
        *)
            ret=1
            ;;
    esac

    if [ $ret -eq 1 ] ; then
        log_info "config file parameter error. [${SCRIPT_CONF_FILE}:${parameter_name}]"
        exit 1
    fi

    log_info "config file parameter : ${parameter_name}=${value}"
    return 0
}

# This function reads the configuration file and set the value.
# If the value is omitted, set the default value.
# If invalid value is set, return 1.
# Note) The default value for each item are as follows.
#       MONITOR_INTERVAL      (defualt : 60)
#       NOTICE_TIMEOUT        (defualt : 10)
#       NOTICE_RETRY_COUNT    (default : 12)
#       NOTICE_RETRY_INTERVAL (default : 10)
#       NOTICE_RETRY_TIMEOUT  (default :120)
#       STONITH_WAIT          (default : 30)
#       MAX_CHILD_PROCESS     (default :  3)
#       TCPDUMP_TIMEOUT       (default : 10)
#       IPMI_TIMEOUT          (default :  5)
#       IPMI_RETRY_MAX        (default :  3)
#       IPMI_RETRY_INTERVAL   (default : 10)
# 
# Return value
#   0 : Setting completion
#   1 : Reading failure of the configuration or invalid setting value
set_conf_value () {
    # Read the configuration file
    source $SCRIPT_CONF_FILE > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        log_info "config file read error. [$SCRIPT_CONF_FILE]"
        return 1
    fi

    MONITOR_INTERVAL=${MONITOR_INTERVAL:-60}
    check_config_type 'int' MONITOR_INTERVAL $MONITOR_INTERVAL

    NOTICE_TIMEOUT=${NOTICE_TIMEOUT:-10}
    check_config_type 'int' NOTICE_TIMEOUT $NOTICE_TIMEOUT

    NOTICE_RETRY_COUNT=${NOTICE_RETRY_COUNT:-12}
    check_config_type 'int' NOTICE_RETRY_COUNT $NOTICE_RETRY_COUNT

    NOTICE_RETRY_INTERVAL=${NOTICE_RETRY_INTERVAL:-10}
    check_config_type 'int' NOTICE_RETRY_INTERVAL $NOTICE_RETRY_INTERVAL

    NOTICE_RETRY_TIMEOUT=${NOTICE_RETRY_TIMEOUT:-120}
    check_config_type 'int' NOTICE_RETRY_TIMEOUT $NOTICE_RETRY_TIMEOUT

    STONITH_WAIT=${STONITH_WAIT:-30}
    check_config_type 'int' STONITH_WAIT $STONITH_WAIT

    MAX_CHILD_PROCESS=${MAX_CHILD_PROCESS:-3}
    check_config_type 'int' MAX_CHILD_PROCESS $MAX_CHILD_PROCESS

    TCPDUMP_TIMEOUT=${TCPDUMP_TIMEOUT:-10}
    check_config_type 'int' TCPDUMP_TIMEOUT $TCPDUMP_TIMEOUT

    IPMI_TIMEOUT=${IPMI_TIMEOUT:-5}
    check_config_type 'int' IPMI_TIMEOUT $IPMI_TIMEOUT

    IPMI_RETRY_MAX=${IPMI_RETRY_MAX:-3}
    check_config_type 'int' IPMI_RETRY_MAX $IPMI_RETRY_MAX

    IPMI_RETRY_INTERVAL=${IPMI_RETRY_INTERVAL:-10}
    check_config_type 'int' IPMI_RETRY_INTERVAL $IPMI_RETRY_INTERVAL

    LOG_LEVEL=${LOG_LEVEL:-10}
    check_config_type 'string' LOG_LEVEL $LOG_LEVEL

    REGION_ID=${REGION_ID:-""}
    check_config_type 'string' REGION_ID $REGION_ID

    return 0
}

# This function gets the NIC that is used for intercommunication of corosync based on
# the contents of /etc/corosync/corosync.conf.
#
# Argument
#   $1 : Value of bindnetabbr is set in /etc/corosync/corosync.conf
# Return value
#   0 : Success to get
#   1 : Fail to get(Detect /etc/corosync/corosync.conf of invalid setting value)
get_mcast_nic () {
    BIND_NET_ADDR=$1
    BIND_NET_ADDR=`echo ${BIND_NET_ADDR} | sed -e 's/\.0$//g'`
    sudo ifconfig > ${TMP_IFCONFIG_FILE}

    if [ `grep "${BIND_NET_ADDR}" ${TMP_IFCONFIG_FILE} | wc -l` -eq 0 ]; then
        return 1
    fi

    S_LINES=`cat ${TMP_IFCONFIG_FILE} | grep -n -e "^[a-z]" -e "^[0-9]" | cut -d":" -f1`
    E_LINE_DEFAULT=`cat -n ${TMP_IFCONFIG_FILE} | tail -n 1 | awk '{print $1}'`
    for S_LINE in ${S_LINES}
    do
        S_LINE=`expr ${S_LINE} + 1`
        E_LINE=`cat ${TMP_IFCONFIG_FILE} | tail -n +${S_LINE} | egrep -n -m 1 -e "^[a-z]" -e "^[0-9]" | cut -d":" -f1`

        if [ -z "${E_LINE}" ]; then
            E_LINE=${E_LINE_DEFAULT}
        else
            E_LINE=`expr ${S_LINE} + ${E_LINE} - 1 - 1`
        fi

        if [ `cat ${TMP_IFCONFIG_FILE} | sed -n "${S_LINE},${E_LINE}p" | grep "${BIND_NET_ADDR}" | wc -l` -ne 0 ]; then
            break
        fi
    done

    S_LINE=`expr ${S_LINE} - 1`
    MCAST_NIC=`cat -n ${TMP_IFCONFIG_FILE} | grep " ${S_LINE}" | awk '{print $2}'`

    return 0
}

# This function checks whether the HB line is alive
# Return value 
#   0 : The HB line is alive.
#   1 : The HB line is not alive.
#   2 : Detect /etc/corosync/corosync.conf of invalic setting value
check_hb_line () {
    # If the heartbeat is not starting, it is not required to execute tcpdump command.
    sudo service corosync status > /dev/null 2>&1
    RET_CORO=$?
    sudo service pacemaker status > /dev/null 2>&1
    RET_PACE=$?
    if ! [ ${RET_CORO} -eq 0 ] || ! [ ${RET_PACE} -eq 0 ]; then
        log_debug "pacemaker or corosync is not running." 
        return 0
    fi

    # Get all the setting of mcastport and bindnetaddr.
    MCAST_PORTS=`grep "mcastport:" ${HA_CONF} | awk '{print $2}'`
    BIND_NET_ADDRS=`grep "bindnetaddr:" ${HA_CONF} | awk '{print $2}'`

    array_mcast_ports=(`echo ${MCAST_PORTS}`)
    array_bind_net_addrs=(`echo ${BIND_NET_ADDRS}`)

    if [ -z "${MCAST_PORTS}" ] ||
       [ -z "${BIND_NET_ADDRS}" ] ||
       [ ${#array_bind_net_addrs[*]} -ne ${#array_mcast_ports[*]} ]; then
        log_debug "${HA_CONF} has incorrect parameters."
        return 2
    fi

    NIC_SUCCESS_FLG=0
    results=""
    loop_count=0
    while [ ${loop_count} -lt ${#array_bind_net_addrs[*]} ]
    do
        MCAST_PORT=${array_mcast_ports[${loop_count}]}
        MCAST_NIC=""
        # Get the NIC that is used for multicast from the values set in bindnetaddr.
        get_mcast_nic ${array_bind_net_addrs[$loop_count]}
        if [ $? -ne 0 ]; then
            log_debug "${HA_CONF} has incorrect parameters."
            return 2
        fi

        log_debug "read mcast port from ${HA_CONF} -> ${MCAST_PORT}"
        log_debug "read mcast nic from ${HA_CONF} -> ${MCAST_NIC}"

        timeout $TCPDUMP_TIMEOUT sudo tcpdump -c 1 -p -i ${MCAST_NIC} port ${MCAST_PORT} > /dev/null 2>&1
        result=$?
        if [ $result -eq 0 ]; then
            NIC_SUCCESS_FLG=1
            log_debug "tcpdump hb line (${MCAST_NIC}) ok."
            break
        else
            log_debug "tcpdump hb line (${MCAST_NIC}) fail. [exit-code: $result]"
            results+="$result "
        fi
        loop_count=`expr $loop_count + 1`
    done

    if [ ${NIC_SUCCESS_FLG} -eq 0 ]; then
        log_info "tcpdump hb line fail. [exit-code: $results]"
        return 1
    fi
    return 0
}

# This function checks the heartbeat state of the own node
# Return value 
#   0 : Stable state
#   1 : The heartbeat is stopped state
#   2 : Unstable state (during state transitions)
check_hb_status()
{
    OWN_NODE=`uname -n`

    sudo crmadmin -S ${OWN_NODE,,} 1> $TMP_CRMADM_FILE 2>/dev/null
    if [ $? -ne 0 ]; then
        # The heartbeat is not running (or during get state).
        log_debug "Heartbeat in the own node doesn't run."
        rm -f $TMP_CRMADM_FILE
        return 1
    fi

    grep -v -e S_IDLE -e S_NOT_DC $TMP_CRMADM_FILE 1>/dev/null 2>&1
    if [ $? -eq 0 ]; then
        # The heartbeat is unstable state (or during state transitions).
        log_debug "Heartbeat is in an unstable state."
        rm -f $TMP_CRMADM_FILE
        return 2
    fi

    rm -f $TMP_CRMADM_FILE
    log_debug "Heartbeat is in a stable state."
    return 0
}

# This function executes the crm_mon command and hold result
# Return value
#   0 : Normal termination
#   1 : Fail to execute the crm_command
run_crm_mon () {
    sudo crm_mon -A -1 >$TMP_CRM_MON_FILE
    result=$?
    if [ $result -ne 0 ]; then
        log_debug "crm_mon fail. [exit-code: $result]"
        return 1
    else
        # Count the number of RA.
        if [ $RA_COUNT -eq 0 ]; then
            group_define=`sudo crm configure show | grep "^group grp_" | sed -n '$p' | cut -d" " -f3-`
	    result=$?
            if [ ! -n "$group_define" ] && ! [ "$result" -eq 0 ] ; then
                log_debug "cib is not configured."
                return 1
            fi
            tmp_array=(`echo $group_define`)
            ln=`echo $((${#group_define}))`
            last_word=`echo ${group_define} | cut -c ${ln}`
            if [ $last_word != "\\" ]; then
                RA_COUNT=${#tmp_array[*]}
            else
                RA_COUNT=`expr ${#tmp_array[*]} - 1`
            fi
        fi
    fi
    log_debug "`cat $TMP_CRM_MON_FILE`"

    # Check whether there is the quorum.
    grep "partition WITHOUT quorum" $TMP_CRM_MON_FILE  > /dev/null 2>&1
    result=$?
    if [ $result -eq 0 ]; then
        log_info "$MY_NODE_NAME is no-quorum."
    fi

    return 0
}

# This function creates the node state file
make_status_file () {
    touch $STATUS_FILE
    count_cluster_nodes
    work_count=$?
    n=0
    while [ $n -lt $work_count ]
    do
        check_node_status ${nodes_array[$n]}
        result=$?
        append_status_file ${nodes_array[$n]} $result
        n=`expr $n + 1`
    done
}

# This function analyzes the output of crm_mon and count the number of cluster node.
# And it stores node name in array in this function.
# Return value
#   The number of cluster node
count_cluster_nodes () {
    # Initialize the array
    nodes_array=()

    # Count the number of Online node.
    online_nodes=`cat $TMP_CRM_MON_FILE | grep ^Online | sed -e 's/\s\{1,\}/ /g' | sed -e 's/ \]$//g' | cut -d" " -f3-`
    log_debug "online nodes : $online_nodes"
    if [ -n "$online_nodes" ]; then
        nodes_array+=(`echo $online_nodes`)
    fi

    # Count the number of OFFLINE node.
    offline_nodes=`cat $TMP_CRM_MON_FILE | grep ^OFFLINE | sed -e 's/\s\{1,\}/ /g' | sed -e 's/ \]$//g' | cut -d" " -f3-`
    log_debug "offline nodes : $offline_nodes"
    if [ -n "$offline_nodes" ]; then
        nodes_array+=(`echo $offline_nodes`)
    fi

    # Count the number of except for Online, OFFLINE node.
    other_nodes=`cat $TMP_CRM_MON_FILE | grep ^Node | grep -v Attributes | sed -e 's/\s\{1,\}/ /g' | cut -d" " -f2`
    log_debug "other nodes : $other_nodes"
    if [ -n "$other_nodes" ]; then
        nodes_array+=(`echo $other_nodes`)
    fi

    return ${#nodes_array[*]}
}

# This function checks startup state of node's RA.
# Argument
#   $1 : Node name
# Return value
#   0 : Started state
#         Node is online, and state of all RA is "Started"
#   1 : Stopped state
#         UNCLEAN, OFFLINE, pending, standby
#   2 : Starting or Stopping state
#         Node is online,  and mixed "RA of Started" and "RA of Stopped"
check_node_status () {
    online_nodes=`cat $TMP_CRM_MON_FILE | grep ^Online | sed -e 's/\s\{1,\}/ /g' | sed -e 's/ \]$//g' | cut -d" " -f3-`
    # Check whether the node of argument is "Online".
    if [ "`echo $online_nodes | grep -e "$1 " -e "$1$"`" ]; then
        # Check whether the node of state of all RA is "Started".
        START_RA_COUNT=`grep "Started $1 " $TMP_CRM_MON_FILE | grep -v stonith | wc -l`
        if [ $START_RA_COUNT -eq $RA_COUNT ] || [ $RA_COUNT -eq -1 ]  ; then
            # Node is online and state of all RA is "Started"(startup state)
            return 0
        else
            # There is "Stopped" even one(Starting or Stopping).
            return 2
        fi
    else
        # In spite of "UNCLEAN" or "OFFLINE" or "pending" or "standby",
        # if RA of "Started" exists, consider state as starting state or stopping state.
        other_node_ra=`grep "Started $1 " $TMP_CRM_MON_FILE | grep -v stonith | wc -l`
        if [ $other_node_ra -ne 0 ] ; then
            return 2
        # "UNCLEAN" or "OFFLINE" or "pending" or "standby"(stopped)
        else
            return 1
        fi
    fi
}

# This function writes in the node state file
# Argument 
#   $1 : node name
#   $2 : node state(0:Started, 1:Stopped, 2:Starting or Stopping)
append_status_file () {
    if [ $2 -eq 0 ]; then
        node_status="$NODE_STATUS_STARTED"
    elif [ $2 -eq 1 ]; then
        node_status="$NODE_STATUS_STOPPED"
    else
        node_status="$NODE_STATUS_UNKNOWN"
    fi

    file_lock $STATUS_FILE
    echo "$1 $node_status" >> $STATUS_FILE
    file_unlock
}

# This function analyzes the state of the node specified by the argument from the result of crm_mon,
# and if the nodes state are different from the last state, notify to the resource management.
# Argument
#   $1 : Node name(1)
#   $2 : Node name(2)
#   ...
#   $n : node name(n)
#   Node name that are passed by arguments is multiple.
#   If nothing is passed to the argument, immediate return.
parse_node_status () {
    if [ $# -eq 0 ]; then
        return 0
    fi

    work_count=$#
    n=0
    while [ $n -lt $work_count ]
    do
        check_node_status $1
        result1=$?
        if [ $result1 -eq 0 ]; then
            EVENT_TYPE="1"
            START_TIME=`date +'%Y%m%d%H%M%S'`
            END_TIME=$START_TIME
        elif [ $result1 -eq 1 ]; then
            EVENT_TYPE="2"
            START_TIME=`date +'%Y%m%d%H%M%S'`
            END_TIME="null"
        fi
        compare_status_file $1 $result1
        result2=$?
        if [ $result2 -eq 1 ]; then
            mkdir -p $JSON_DIR
            JSON_FILE="${JSON_DIR}/${BASE_NAME}_$1.json"
            make_notice_data $1 > $JSON_FILE
            send_to_rm $1 $JSON_FILE
        fi
        shift
        n=`expr $n + 1`
    done

    return 0
}

# This function compares state of last node with state of this time node,
# and if they are different, rewrite the state file.
# It is called from child process.
#
# Arguments
#   $1 :  Node name
#   $2 :  Node state(0:Started, 1:Stopped, 2:Starting or Stopping)
# return value
#   0 : There is not change from the last state and notification to the resource is not required.  
#   1 : There is change from the last state and notification to the resource is required.
#   2 : There is change from the last state and notification to the resource is not required.
compare_status_file () {
    # Check whether state of this time node changed from state of last time node.
    last_node_status=`grep "$1 " $STATUS_FILE | cut -d" " -f2`

    # If node name that does not exist in the node state file, add it's node name to the file.
    if [ ! -n "$last_node_status" ]; then
        append_status_file $1 $2
        return 2
    fi

    if [ $2 -eq 0 ]; then
        # If state of this time node is "Started" and state of last time node is "Started",
        if [ $last_node_status = $NODE_STATUS_STARTED ]; then
            return 0
        # If state of this time node is "Started" and
        # state of last time node is "Started" or "Stopping" or "Starting" or "Unknown",
        else
            change_status_file $1 $2 $last_node_status
            return $?
        fi
    elif [ $2 -eq 1 ]; then
        # If state of this time node is "Stopped" and state of last time node is "Stopped",
        if [ $last_node_status = $NODE_STATUS_STOPPED ]; then
            return 0
        # If state of this time node is "Stopped" and
        # state of last time node is "Started" or "Stopping" or "Starting" or "Unknown",
        else
            change_status_file $1 $2 $last_node_status
            return $?
        fi
    # If state of this time node is "Stopping" or "Starting" or "Unknown",
    else
        change_status_file $1 $2 $last_node_status
        return $?
    fi
}

# This function rewrites the state file.
# Return the necessity of notification return code
# 
# Argument
#   $1 : Node name
#   $2 : Node state(0:Started, 1:Stopped, 2:Starting or Stopping)
#   $3 : State of the last node is specified in the node state file
# Return value
#   1 : Notification to the resource management is required
#   2 : Notification to the resource management is not required
change_status_file () {
    # If state of this time node is "Started",
    if [ $2 -eq 0 ]; then
        node_status="$NODE_STATUS_STARTED"
        # If state of this time node is "Stopping" or "Unknown", notification is not sent.
        if [ $3 = $NODE_STATUS_STOPPING ] ||
           [ $3 = $NODE_STATUS_UNKNOWN ]; then
            retval=2
        else
            retval=1
        fi
    # If state of this time node is "Stopped",
    elif [ $2 -eq 1 ]; then
        node_status="$NODE_STATUS_STOPPED"
        # If state of this time node is "Starting" or "Unknown", notification is not sent.
        if [ $3 = $NODE_STATUS_STARTING ] ||
           [ $3 = $NODE_STATUS_UNKNOWN ]; then
            retval=2
        else
            retval=1
        fi
    # If state of this time node is "Starting" or "Stopping" or "Unknown",
    else
        if [ $3 = $NODE_STATUS_STARTED ]; then
            node_status="$NODE_STATUS_STOPPING"
        elif [ $3 = $NODE_STATUS_STOPPED ]; then
            node_status="$NODE_STATUS_STARTING"
        else
            node_status="$3"
        fi
        # Notification is not sent.
        retval=2
    fi

    file_lock $STATUS_FILE
    sed -i "s/$1 $last_node_status/$1 $node_status/g" $STATUS_FILE
    file_unlock

    return $retval
}


# This function creates data to be notified to the resource management. 
# It is called from the child process.
# 
# Argument
#   $1 : Node name
make_notice_data () {
    TMP_RULE=`sudo crm configure show | grep "rule" | grep -i -e "100: #uname eq $1 " -e "100: #uname eq $1$" | grep -v "stonith"`
    L_HOST=""
    P_HOST=`echo ${TMP_RULE} | awk '{print $5}'`
    if [ ${STONITH_TYPE} = "ssh"  ] ; then
       P_HOST=$1
    fi

    # Usually, the route which shuldn't pass
    # (Abnormal states such as resource group name is "_grp", or physical host name is ""(empty string).
    if [ ! -n "${P_HOST}" ]; then P_HOST="UnknownPhysicalHost"; fi

    get_tzname_daylight

    if [ ${EVENT_TYPE} = "1" ]; then
        TIME="${END_TIME}"
    else
        TIME="${START_TIME}"
    fi

    DETAIL=1

    # In the case of stop notification, check whether the opposing node has stopped securety.
    if [ ${EVENT_TYPE} = "2" ] ; then
        DETAIL=2

	# adhoc setting for test
	if [ ${STONITH_TYPE} = "ipmi" ] ; then

	    # Get the value which is required for ipmitool command execution.
	    IPMI_RAS=`sudo crm configure show | grep "^primitive.*stonith:external/ipmi" | awk '{print $2}'`
	    for IPMI_RA in ${IPMI_RAS}
	    do
	        IPMI_HOST=`sudo crm resource param ${IPMI_RA} show hostname`
	        if [ "${IPMI_HOST}" = "${P_HOST}" ]; then
		break
	        fi
	    done
	    userid=`sudo crm resource param ${IPMI_RA} show userid`
	    passwd=`sudo crm resource param ${IPMI_RA} show passwd`
	    interface=`sudo crm resource param ${IPMI_RA} show interface`
	    ipaddr=`sudo crm resource param ${IPMI_RA} show ipaddr`

	    LOOP_COUNT=0
	    while [ ${LOOP_COUNT} -lt `expr ${IPMI_RETRY_MAX} + 1` ]
	    do
	        POWER_STATUS=`timeout ${IPMI_TIMEOUT} sudo ipmitool -U ${userid} -P ${passwd} -I ${interface} -H ${ipaddr} power status 2>&1`
	        RET1=$?
	        echo ${POWER_STATUS} | grep "Power is off" > /dev/null 2>&1
	        RET2=$?
	        # If the opposing node has stopped securely, pass route of the notification.
	        if [ ${RET1} -eq 0 ] && [ ${RET2} -eq 0 ]; then
	            log_debug "Node $1 power is off."
	    	    break
	        fi
	        # If the opposing node has stopped securely, recheck after sleep.
	        log_debug "Sleep to get power status of node $1"
	        sleep ${IPMI_RETRY_INTERVAL}
	        LOOP_COUNT=`expr ${LOOP_COUNT} + 1`
	    done

	    # If get the state of "Power is on" at the final, the detail is specified in "3".
	    if [ ${LOOP_COUNT} -eq `expr ${IPMI_RETRY_MAX} + 1` ] && [ ${RET1} -eq 0 ]; then
	        log_info "$1 info : Node $1 power is still on."
	        DETAIL="3"
	    # If get the state of "Unknown", the detail is specified in "4".
    	    elif [ ${LOOP_COUNT} -eq `expr ${IPMI_RETRY_MAX} + 1` ] && [ ${RET1} -ne 0 ]; then
	        log_info "$1 info : Couldn't get power status of node $1."
	        DETAIL="4"
	    fi
	fi
    fi

    # Consider the port number
    # that is used for intercommunication of Pacemaker+corosync as the cluster identifier.
    ADDR=`grep "mcastaddr:" ${HA_CONF} | awk '{print $2}' | tail -1`
    PORT=`grep "mcastport:" ${HA_CONF} | awk '{print $2}' | tail -1`
    CLUSTER_PORT="${ADDR}:${PORT}"

    echo "{"
    cat <<NOTICE_DATA_END
    "id": "${ID}",
    "type": "${TYPE}",
    "regionID": "${REGION_ID}",
    "hostname": "${P_HOST}",
    "uuid": "${L_HOST}",
    "time": "${TIME}",
    "eventID": "${EVENT_ID}",
    "eventType": "${EVENT_TYPE}",
    "detail": "${DETAIL}",
    "startTime": "${START_TIME}",
NOTICE_DATA_END
    if [ ${END_TIME} != "null" ]; then
        echo "    \"endTime\": \"${END_TIME}\"",
    else
        echo "    \"endTime\": null",
    fi
cat <<NOTICE_DATA_END
    "tzname": "${TZ_NAME}",
    "daylight": "${DAYLIGHT}",
    "cluster_port": "${CLUSTER_PORT}"
NOTICE_DATA_END
    echo "}"
}

# This function gets timezone and the daylight saving time, set time to varlable.
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
# Arguments
#   $1 : Json file name
# return value
#   0 : Notification is sucessful.
#   1 : Notification is failed.
send_to_rm () {
    log_info "$1 info : $BASE_NAME : begin"

    if [ -z $RM_URL ]; then
        log_info "$1 info : RM server URL is not set."
        log_info "$1 info : $BASE_NAME : end"
        return 0
    fi
    NOTICE_OPTS="--silent"
    NOTICE_OPTS+=" --header \"Content-Type:application/json\""
    NOTICE_OPTS+=" --write-out \"HTTP_CODE=%{response_code}\n\""
    NOTICE_OPTS+=" --max-time ${NOTICE_TIMEOUT}"
    NOTICE_OPTS+=" --retry ${NOTICE_RETRY_COUNT}"
    NOTICE_OPTS+=" --retry-delay ${NOTICE_RETRY_INTERVAL}"
    NOTICE_OPTS+=" --retry-max-time ${NOTICE_RETRY_TIMEOUT}"
    NOTICE_OPTS+=" --data @$2"
    log_info "$1 info : $NOTICE_PROGRAM $NOTICE_OPTS $RM_URL"
    log_info "$1 info : data : `cat $2`"

    retry_count=1
    while [ ${retry_count} -le ${NOTICE_RETRY_COUNT} ]
    do
        $NOTICE_PROGRAM $NOTICE_OPTS $RM_URL >$NOTICE_OUTPUT
        result=$?
        if [ $result -eq 7 ]; then
            log_debug "$1 info : $NOTICE_PROGRAM fail. Connection refused.(${retry_count}) [exit-code: $result]"
            sleep ${NOTICE_RETRY_INTERVAL}
            retry_count=`expr ${retry_count} + 1`
            continue
        elif [ $result -ne 0 ]; then
            log_info "$1 info : $NOTICE_PROGRAM fail. [exit-code: $result]"
            log_info "$1 info : $BASE_NAME : end"
            return 1
        else
            HTTP_STATUS_CODE="`grep HTTP_CODE $NOTICE_OUTPUT | tail -1 | sed 's/'.*HTTP_CODE='//g'`"
            log_info "$1 info : Notice response. [status-code: $HTTP_STATUS_CODE]"
            break
        fi
    done

    if [ ${retry_count} -gt ${NOTICE_RETRY_COUNT} ]; then
        log_info "$1 info : $NOTICE_PROGRAM fail. Connection refused.(Tried 'curl' ${NOTICE_RETRY_COUNT} times.) [exit-code: $result]"
        log_info "$1 info : $BASE_NAME : end"
        return 1
    else
        log_info "$1 info : $BASE_NAME : end"
        return 0
    fi
}

# main route
log_info "begin"

# If node state file exists at the initial startup, delete the file.
if [ -f $STATUS_FILE ]; then
    sudo rm -f $STATUS_FILE
fi

while true
do
    # If invalid value is set in the configuration file, set the default value.
    set_conf_value
    if [ $? -ne 0 ]; then
       break 
    fi

    # Initialize
    script_initialize

    # Check whether HB line is normal.
    check_hb_line
    if [ $? -ne 0 ]; then
        case $? in
        1)
            sleep $STONITH_WAIT
            ;;
        2)
            script_finalize 1
            sleep $MONITOR_INTERVAL
            continue
            ;;
        esac
    fi

    # Check the heartbeat state of the own node.
    check_hb_status
    if [ $? -ne 0 ]; then
        case $? in
        1)
            script_finalize 0
            ;;
        2)
            script_finalize 1
            ;;
        esac
        sleep $MONITOR_INTERVAL
        continue
    fi

    # Get output result of crm_mon.
    run_crm_mon
    ret=$?
    if [ $ret -ne 0 ]; then
        script_finalize 0
        sleep $MONITOR_INTERVAL
        continue
    fi

    # If state file of last node is not exsits, create state file, 
    # and write current state to state file.
    if [ ! -e $STATUS_FILE ]; then
        make_status_file
        log_debug "`cat $STATUS_FILE`"
        sleep $MONITOR_INTERVAL
        continue
    fi

    # Count the number of cluster node.
    count_cluster_nodes
    result=$?
    if [ $result -eq 0 ]; then
        script_finalize 0
        sleep $MONITOR_INTERVAL
        continue
    fi

    # If the number of nodes is fewer than the maximum number of child process,
    # Child process should start only the number of the node.
    if [ $result -le $MAX_CHILD_PROCESS ]; then
        MAX_CHILD_PROCESS=$result
    fi

    # Get the minimum number of nodes that are taken care of by the child process.
    child_min_work=`expr $result / $MAX_CHILD_PROCESS`
    # Get the maximum number of nodes that are taken care of by the child process.
    child_max_work=`expr $child_min_work + 1`
    # Get the number of the child process
    # that takes care of the number of child_max_work nodes.
    max_work_count=`expr $result % $MAX_CHILD_PROCESS`

    # Get the node name(multiple) that is processed by the child process, 
    # pass its node name to child process
    jobsrunning=0
    n=0
    m=0
    # Loop processing is executed only by the MAX_CHILD_PROCESS.
    while [ $jobsrunning -lt $MAX_CHILD_PROCESS ]
    do
        work=0
        param=""
        # If the child process take care of only the "max_work_count" nodes,
        if [ $m -lt $max_work_count ]; then
            # Loop processing is executed only by the maximun number of nodes
            # that are taken care of by the child process.
            while [ $work -lt $child_max_work ]
            do
                # Only if node name is not empty string
                # and it is not own node name, pass it to child process.
                if [ -n "${nodes_array[$n]}" ] && [ ${nodes_array[$n]} != $MY_NODE_NAME ]; then
                    param+="${nodes_array[$n]} "
                fi
                work=`expr $work + 1`
                n=`expr $n + 1`
            done
        # If the child process take care of only the "min_work_count" nodes,
        else
            # Loop processing is executed only by the maximun number of nodes
            # that are taken care of by the child process.
            while [ $work -lt `expr $child_min_work` ]
            do
                # Only if node name is not empty string
                # and it is not own node name, pass it child process.
                if [ -n "${nodes_array[$n]}" ] && [ ${nodes_array[$n]} != $MY_NODE_NAME ]; then
                    param+="${nodes_array[$n]} "
                fi
                work=`expr $work + 1`
                n=`expr $n + 1`
            done
        fi
        parse_node_status $param &
        jobsrunning=`expr $jobsrunning + 1`
    done
    wait

    log_debug "`cat $STATUS_FILE`"

    script_finalize 1
    sleep $MONITOR_INTERVAL
done

log_info "end"

