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

import os
import syslog
import time
from pprint import pformat
import libvirt_eventfilter as evf

###################################################
# Global variable declaration
###################################################
if os.path.dirname(__file__):           # load by import
    dir_path=os.path.dirname(__file__)
    CONFIG_FILE='/etc/instancemonitor/instancemonitor.conf'  # Callback configuration file
    #LOG_FILENAME=dir_path+'/eventCallback.log'  # Log output destination
    LOG_FILENAME=''                     # If the log is not output
else:                                   # load as main (debug)
    CONFIG_FILE='/etc/instancemonitor/instancemonitor.conf'  # Callback configuration file
    LOG_FILENAME='./eventCallback.log'  # Log output destination

callback_config={}                          # Area that holds the set of callback

syslog_level={'debug': syslog.LOG_DEBUG,
              'info': syslog.LOG_INFO, 'notice': syslog.LOG_NOTICE,
              'warning': syslog.LOG_WARNING, 'err': syslog.LOG_ERR}
syslog_facility={'kern': syslog.LOG_KERN,
                 'user': syslog.LOG_USER, 'daemon': syslog.LOG_DAEMON,
                 'local0': syslog.LOG_LOCAL0, 'local1': syslog.LOG_LOCAL1,
                 'local2': syslog.LOG_LOCAL2, 'local3': syslog.LOG_LOCAL3,
                 'local4': syslog.LOG_LOCAL4, 'local5': syslog.LOG_LOCAL5,
                 'local6': syslog.LOG_LOCAL6, 'local7': syslog.LOG_LOCAL7}

#################################
# Function name:
#   libvirtEventCallback
#
# Function overview:
#  Callback processing be executed as result of the libvirt event filter
#   Sample implementation
#    Event is sent as HTTP POST
#    The content of sending and receiving is output to the log
#
#  Argument：
#    eventID           : Event ID notify to the callback function
#    eventType         : Event type notify to the callback function
#    detail            : Event code notify to the callback function
#    uuID              : Uuid notify to the callback function
#    noticeID          : Unique ID for each notification contents notify to the callback function
#    noticeType        : Notice type notify to the callback function
#    hostname          : Server host name of the source an event occur notify to the callback function
#    currentTime       : Time the event occurred notify to the callback function
#    tz_name_str       : Time zone notify to the callback function
#    time_daylight_str : The daylight time notify to the callback function
#
# Return value：
#   None
#
#################################

def libvirtEventCallback(eventID, eventType, detail, uuID, noticeID, noticeType, hostname, currentTime, tz_name_str, time_daylight_str):
    global callback_config

    # Gets the values in the configuration file.
    if not callback_config:
        callback_config_setup()

    regionID=callback_config['regionID']
    http_url=callback_config['url']
    retry_timeout=int(callback_config['retry_timeout'])

    # Output to the syslog.
    evf.syslogout('libvirt Event: id={0} type={1} regionID={2} hostname={3} uuid={4} time={5} eventID={6} eventType={7} detail={8} tzname={9} daylight={10} cluster_port=null'.format(
           noticeID, noticeType, regionID, hostname, uuID, currentTime, eventID, eventType, detail, tz_name_str, time_daylight_str ),
           callback_config['logLevel'], callback_config['logFacility'])

    # If the URL is empty string, output to the log. And terminate.
    if not http_url:
        logmsg("RM server URL is not set.")
        return

    # Set the event to the dictionary.
    event={'id': noticeID, 'type': noticeType, 'regionID': regionID,
            'hostname': hostname, 'uuid':uuID, 'time': currentTime,
            'eventID': eventID, 'eventType': eventType, 'detail': detail,
            'tzname': tz_name_str, 'daylight': time_daylight_str, 'cluster_port': ''}

    # Retry until successful.
    for i in range(int(callback_config['retry'])):
        logmsg("POST message: " + pformat(event))
        # HTTP POST
        try:
            resp, content = post_event(url=http_url, event=event, retry_timeout=retry_timeout)
            # Response checking
            if int(resp['status'])/100 == 2:
                logmsg("OK Response: status(" + pformat(resp['status']) +
                       ") : " + pformat(content))
                return    # Normal termination
            # Error
            logmsg("Error Response(" + str(i+1) + "): status(" + pformat(resp['status']) +
                   ") : " + pformat(content), True)
        except socket.timeout, e:
            # Timeout
            logmsg("Error Response(" + str(i+1) + "): No response. Timeout.", True)
            pass
        except socket.error, e:
            # Connection failure
            logmsg("Error Response(" + str(i+1) + "): Socket error. (" + str(e) + ")" , True)
            pass
        # "sleep" of the specified interval
        time.sleep(float(callback_config['interval']))
    # Retry over
    logmsg('HTTP Request Retry Over. url={0} id={1} type={2} regionID={3} hostname={4} uuid={5} time={6} eventID={7} eventType={8} detail={9} tzname={10} daylight={11}'.format(
           http_url, noticeID, noticeType, regionID, hostname, uuID, currentTime, eventID, eventType, detail, tz_name_str, time_daylight_str), True)


#################################
# Function name:
#   callback_config_setup
#
# Function overview:
#   Read out the config setting of callback processing.
#   Settings are stored in the global_callback_config as dictionary type.
#
# Argument:
#   None
#
# Return value:
#   None
#
#################################
import ConfigParser

def callback_config_setup():
    global callback_config

    inifile = ConfigParser.SafeConfigParser()
    inifile.read(CONFIG_FILE)
    ll = inifile.get('callback', 'log_level')
    try:
        logLevel = syslog_level[ll]
    except KeyError:
        logmsg(CONFIG_FILE+": invalid config log_level " + ll ,True)
    lf = inifile.get('callback', 'log_facility')
    try:
        logFacility = syslog_facility[lf]
    except KeyError:
        logmsg(CONFIG_FILE+": invalid config log_facility " + lf ,True)
    callback_config={'url': inifile.get('callback', 'url'),
                     'regionID': inifile.get('callback', 'regionID'),
                     'retry': inifile.get('callback', 'retry'),
                     'interval': inifile.get('callback', 'interval'),
                     'logLevel': logLevel, 'logFacility': logFacility,
                     'retry_timeout': inifile.get('callback', 'retry_timeout')}


#################################
# Function name:
#    post_event
#
# Function overview:
#   The message is converted to JSON format. And it is sent by the HTTP POST method.
#   Encode to the JSON-format by using simplejson.
#   If simplejson is not available, json is substituted.
#
# Argument：
#   url           : Notification destination URL
#   event         : Message(dictionary)
#   retry_timeout : Timeout value of the processing which depends of the notification once
#
# Return value:
#   Http().request result
#
#################################
from httplib2 import Http
import socket
try:
    # For c speedups
    from simplejson import loads, dumps
except ImportError:
    from json import loads, dumps
def post_event(url, event, retry_timeout):
    return Http(timeout=retry_timeout).request(
        uri=url,
        method='POST',
        headers={'Content-Type': 'application/json; charset=UTF-8'},
        body=dumps(event))


#################################
# Function name:
#   logmsg
#
# Function overview:
#   Output to the log.
#   Output to the logfile that is specified in the LOGFILE_NAME.
#   The same contents as LOGFILE_NAME are output to syslog.
#
# Argument:
#   msg : The message which outputs to the log
#
# Return value:
#   None
#
#################################
import logging

def logmsg(msg, err=False):
    if LOG_FILENAME:
        logging.basicConfig(filename=LOG_FILENAME, filemode='w', level=logging.DEBUG,
                            format='%(asctime)s %(levelname)s %(message)s')
        logging.debug(msg)
    if err:
        evf.error_log(msg)

# for debug
if __name__ == "__main__":
    libvirtEventCallback(5, 10, 1, 'a-b-c', 'd-e-f', 'type', 'host', 'YYYYmmddHHMMSS')
