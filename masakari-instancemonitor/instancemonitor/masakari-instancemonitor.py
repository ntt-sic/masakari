#!/usr/bin/python -u
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
import sys
import os
import getopt
import threading
import libvirt
import errno
import time
import daemon
import libvirt_eventfilter as evf
from libvirt_eventfilter_table import *
import libvirt_callback

###################################################
# Global variable declaration
###################################################
# This keeps track of what thread is running the event loop,
# (if it is run in a background thread)
eventLoopThread = None


###################################################
# Define event loop function
###################################################
# Directly run the event loop in the current thread
def virEventLoopNativeRun():
    while True:
        libvirt.virEventRunDefaultImpl()

# Spawn a background thread to run the event loop


def virEventLoopNativeStart():
    global eventLoopThread
    libvirt.virEventRegisterDefaultImpl()
    eventLoopThread = threading.Thread(target=virEventLoopNativeRun,
                                       name="libvirtEventLoop")
    eventLoopThread.setDaemon(True)
    eventLoopThread.start()


##########################################################################
# Define event callback function
##########################################################################
def myDomainEventCallback(conn, dom, event, detail, opaque):
    evf.virEventFilter(VIR_DOMAIN_EVENT_ID_LIFECYCLE,
                       event, detail, dom.UUIDString())


def myDomainEventRebootCallback(conn, dom, opaque):
    evf.virEventFilter(VIR_DOMAIN_EVENT_ID_REBOOT, -1, -1, dom.UUIDString())


def myDomainEventRTCChangeCallback(conn, dom, utcoffset, opaque):
    evf.virEventFilter(VIR_DOMAIN_EVENT_ID_RTC_CHANGE, -
                       1, -1, dom.UUIDString())


def myDomainEventWatchdogCallback(conn, dom, action, opaque):
    evf.virEventFilter(VIR_DOMAIN_EVENT_ID_WATCHDOG,
                       action, -1, dom.UUIDString())


def myDomainEventIOErrorCallback(conn, dom, srcpath, devalias, action, opaque):
    evf.virEventFilter(VIR_DOMAIN_EVENT_ID_IO_ERROR,
                       action, -1, dom.UUIDString())


def myDomainEventGraphicsCallback(conn, dom, phase, localAddr, remoteAddr, authScheme, subject, opaque):
    evf.virEventFilter(VIR_DOMAIN_EVENT_ID_GRAPHICS, -
                       1, phase, dom.UUIDString())


def myDomainEventDiskChangeCallback(conn, dom, oldSrcPath, newSrcPath, devAlias, reason, opaque):
    evf.virEventFilter(VIR_DOMAIN_EVENT_ID_DISK_CHANGE, -
                       1, -1, dom.UUIDString())


def myDomainEventIOErrorReasonCallback(conn, dom, srcPath, devAlias, action, reason, opaque):
    evf.virEventFilter(
        VIR_DOMAIN_EVENT_ID_IO_ERROR_REASON, -1, -1, dom.UUIDString())


def myDomainEventGenericCallback(conn, dom, opaque):
    evf.virEventFilter(VIR_DOMAIN_EVENT_ID_CONTROL_ERROR, -
                       1, -1, dom.UUIDString())


#################################
# Function name:
#   usage
#
# Function overview:
#   Output the usage.
#
# Argument:
#   out : Output destination
#
# Return value:
#   None
#
#################################
def usage(out=sys.stderr):
    print >>out, "usage: " + os.path.basename(sys.argv[0]) + " [-hd] [uri]"
    print >>out, "   uri will default to qemu:///system"
    print >>out, "   --help, -h   Print this help message"
    print >>out, "   --debug, -d  Print debug output"


#################################
# Function name:
#   errHandler
#
# Function overview:
#   Output error (libvirtError) message of libvirt library to the syslog.
#
# Argument:
#   ctxt : The name of the error processing
#   err  :  LibvirtError tuple
#
# Return value:
#   None
#
#################################
errno = None


def errHandler(ctxt, err):
    global errno
    # print "libvirt Error(%s)" % (err[2])
    evf.warn_log(err[2])
    errno = err


#################################
# Function name:
#   virtEvent
#
# Function overview:
#   Start event loop look as thread from main thread. And make it daemon thread.
#   Open the connection, and set event callback.
#   Perform periodic monitoring of connection, and when abnormal condition is detected, reconnect.
#
# Argument:
#   uri : libvirt connection driver
#
# Return value:
#   None
#
#################################
def virtEvent(uri):
    # Run a background thread with the event loop
    virEventLoopNativeStart()

    # Connect libbert - If be disconnected, reprocess.
    while True:
        vc = libvirt.openReadOnly(uri)

        # Event callback settings
        callback_ids = []
        cid = vc.domainEventRegisterAny(None, libvirt.VIR_DOMAIN_EVENT_ID_LIFECYCLE,
                                        myDomainEventCallback, None)
        callback_ids.append(cid)
        cid = vc.domainEventRegisterAny(None, libvirt.VIR_DOMAIN_EVENT_ID_REBOOT,
                                        myDomainEventRebootCallback, None)
        callback_ids.append(cid)
        cid = vc.domainEventRegisterAny(None, libvirt.VIR_DOMAIN_EVENT_ID_RTC_CHANGE,
                                        myDomainEventRTCChangeCallback, None)
        callback_ids.append(cid)
        cid = vc.domainEventRegisterAny(None, libvirt.VIR_DOMAIN_EVENT_ID_IO_ERROR,
                                        myDomainEventIOErrorCallback, None)
        callback_ids.append(cid)
        cid = vc.domainEventRegisterAny(None, libvirt.VIR_DOMAIN_EVENT_ID_WATCHDOG,
                                        myDomainEventWatchdogCallback, None)
        callback_ids.append(cid)
        cid = vc.domainEventRegisterAny(None, libvirt.VIR_DOMAIN_EVENT_ID_GRAPHICS,
                                        myDomainEventGraphicsCallback, None)
        callback_ids.append(cid)
        cid = vc.domainEventRegisterAny(None, libvirt.VIR_DOMAIN_EVENT_ID_DISK_CHANGE,
                                        myDomainEventDiskChangeCallback, None)
        callback_ids.append(cid)
        cid = vc.domainEventRegisterAny(None, libvirt.VIR_DOMAIN_EVENT_ID_IO_ERROR_REASON,
                                        myDomainEventIOErrorReasonCallback, None)
        callback_ids.append(cid)
        cid = vc.domainEventRegisterAny(None, libvirt.VIR_DOMAIN_EVENT_ID_CONTROL_ERROR,
                                        myDomainEventGenericCallback, None)
        callback_ids.append(cid)

        # Connection monitoring.
        vc.setKeepAlive(5, 3)
        while vc.isAlive() == 1:
            time.sleep(1)

        # If connection between libvirtd was lost, clear callback connection.
        evf.warn_log('Libvirt Connection Closed Unexpectedly.')
        for cid in callback_ids:
            try:
                vc.domainEventDeregisterAny(cid)
            except:
                pass
        vc.close()
        del vc
        time.sleep(3)


#################################
# Function name:
#   main
#
# Function overview:
#   Check the startup option, and set it.
#   If the URI is not specified, set the default URI.
#   Set the error handler, and executes event loop processing.
#
# Argument:
#   None
#
# Return value:
#   None
#
#################################
def main():
    # Check argument.
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hd", ["help", "debug"])
    except getopt.GetoptError, err:
        usage()
        sys.exit(2)

    for o, a in opts:
        if o in ("-h", "--help"):
            usage(sys.stdout)
            sys.exit()
        if o in ("-d", "--debug"):
            evf.do_debug = True

    if len(args) >= 1:
        uri = args[0]
        # check for validate uri - getVersion not useful
        try:
            vc = libvirt.openReadOnly(uri)
            vc.close()
            del vc
        except:
            print "invalid uri -", uri
            sys.exit(1)
    else:
        uri = "qemu:///system"
    evf.debug_log("Using uri:" + uri)

    # Set callback config
    libvirt_callback.callback_config_setup()

    # set error handler & do event loop
    libvirt.registerErrorHandler(errHandler, 'virtEvent')
    with daemon.DaemonContext():
        virtEvent(uri)


if __name__ == "__main__":
    main()
