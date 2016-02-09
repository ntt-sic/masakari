#!/usr/bin/python
# -*- coding: utf-8 -*-

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

###################################################
# Declaration of import
###################################################
import threading
import os
import sys
import syslog
import socket
import uuid
import datetime
import time
from libvirt_callback import *
from libvirt import *
from libvirt_eventfilter_table import *

###################################################
# Global variable declaration
###################################################
# Hold whether there is debug mode specified by option at the time of program startup.
do_debug = False

#################################
# Function name:
#   debug_log
#
# Function overview:
#   Output to the syslog(LOG_DEBUG level)
#   Only if debug mode is specified by the startup option, output to the syslog.
#
# Argument:
#   msg : Message string
#
# Return value:
#   None
#
#################################
def debug_log(msg):
    if do_debug:
        syslogout(msg)

#################################
# Function name:
#   error_log
#
# Function overview:
#   Output to the syslog(LOG_ERROR level)
#
# Argument:
#   msg : Message string
#
# Return value:
#   None
#
#################################
def error_log(msg):
    syslogout(msg, logLevel=syslog.LOG_ERR)

#################################
# Function name:
#   warn_log
#
# Function overview:
#   Output to the syslog(LOG_WARNING level)
#
# Argument:
#   msg : Message string
#
# Return value:
#   None
#
#################################
def warn_log(msg):
    syslogout(msg, logLevel=syslog.LOG_WARNING)

#################################
# Function name:
#   syslogout
#
# Function overview:
#   Output to the syslog
#
# Argument:
#   msg      : Message string
#   logLevel : Output level to syslog
#              Default is LOG_DEBUG
#
# Return value:
#   None
#
#################################
import logging

def syslogout(msg, logLevel=syslog.LOG_DEBUG, logFacility=syslog.LOG_USER):

    # Output to the syslog.
    arg0=os.path.basename(sys.argv[0])
    host=socket.gethostname()

    logger = logging.getLogger()
    logger.setLevel( logging.DEBUG )

    f = "%(asctime)s " + host + " %(module)s(%(process)d): %(levelname)s: %(message)s"

    formatter = logging.Formatter( fmt=f, datefmt='%b %d %H:%M:%S' )

    fh = logging.FileHandler( filename =
            '/var/log/masakari/masakari-instancemonitor.log' )
    fh.setLevel( logging.DEBUG )
    fh.setFormatter( formatter )

    logger.addHandler( fh )

    if logLevel == syslog.LOG_DEBUG:
        logger.debug( msg )
    elif logLevel == syslog.LOG_INFO or logLevel == syslog.LOG_NOTICE:
        logger.info( msg )
    elif logLevel == syslog.LOG_WARNING:
        logger.warn( msg )
    elif logLevel == syslog.LOG_ERR:
        logger.error( msg )
    elif logLevel == syslog.LOG_CRIT or logLevel == syslog.LOG_ALERT or logLevel == syslog.LOG_EMERGE:
        logger.critical( msg )
    else:
        logger.debug( msg )

    logger.removeHandler( fh )

#################################
# Function name:
#   virEventFilter
#
# Function overview:
#   Filter events from libvirt.
#
# Argument:
#   eventID   : EventID
#   eventType : Event type
#   detail    : Event name
#   uuID      : UUID
#
# Return value:
#   None
#
#################################
def virEventFilter(eventID, eventType, detail, uuID):

    noticeID = str(uuid.uuid4())
    noticeType = 'VM'
    hostname = socket.gethostname()
    t = datetime.datetime.now()
    currentTime = t.strftime('%Y%m%d%H%M%S')

    tz_name = time.tzname
    tz_name_str = str(tz_name)
    tz_name_str = tz_name_str.lstrip('(')
    tz_name_str = tz_name_str.rstrip(')')

    time_daylight = time.daylight
    time_daylight_str = str(time_daylight)

    # All Event Output if debug mode is on.
    debug_log("libvirt Event Received. id=%s type=%s regionID=%s hostname=%s uuid=%s time=%s eventID=%d eventType=%d detail=%d tzname=%s daylight=%s" % (noticeID, noticeType, '<Not set yet>', hostname, uuID, currentTime, eventID, eventType, detail, tz_name_str, time_daylight_str))

    try:
        if detail in event_filter_dic[eventID][eventType]:
            debug_log("Event Filter Matched.")
            # callback Thread Start
            thread=threading.Thread(target=libvirtEventCallback, args=(eventID,
                eventType, detail, uuID, noticeID, noticeType, hostname, currentTime,
                tz_name_str, time_daylight_str))
            thread.start()
        else:
            debug_log("Event Filter Unmatched.")
            pass

    except KeyError:
        debug_log("virEventFilter KeyError")
        pass
    except IndexError:
        debug_log("virEventFilter IndexError")
        pass
    except TypeError:
        debug_log("virEventFilter TypeError")
        pass
    except :
        debug_log("Unexpected error")
        sys.exc_info()[0]
        raise

