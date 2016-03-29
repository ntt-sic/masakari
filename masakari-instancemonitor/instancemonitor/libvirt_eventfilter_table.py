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
#  Import the event definition of libvirt
###################################################
from libvirt import *

###################################################
# Global variable declaration
###################################################
DUMMY = -1        # If is not defined internal , -1 is stored.

########################################################################
#   Enumerate all event that can get.
#   Comment out events that is not targeted in the callback.
########################################################################
event_filter_dic = {
    VIR_DOMAIN_EVENT_ID_LIFECYCLE:
    {
        #        VIR_DOMAIN_EVENT_DEFINED:
        #        (
        #            VIR_DOMAIN_EVENT_DEFINED_ADDED,
        #            VIR_DOMAIN_EVENT_DEFINED_UPDATED
        #        ),
        #        VIR_DOMAIN_EVENT_UNDEFINED:
        #        (
        #            VIR_DOMAIN_EVENT_UNDEFINED_REMOVED,
        #        ),
        #        VIR_DOMAIN_EVENT_STARTED:
        #        (
        #            VIR_DOMAIN_EVENT_STARTED_BOOTED,
        #            VIR_DOMAIN_EVENT_STARTED_MIGRATED,
        #            VIR_DOMAIN_EVENT_STARTED_RESTORED,
        #            VIR_DOMAIN_EVENT_STARTED_FROM_SNAPSHOT
        #        ),
        VIR_DOMAIN_EVENT_SUSPENDED:
        (
            #            VIR_DOMAIN_EVENT_SUSPENDED_PAUSED,
            #            VIR_DOMAIN_EVENT_SUSPENDED_MIGRATED,
            VIR_DOMAIN_EVENT_SUSPENDED_IOERROR,
            VIR_DOMAIN_EVENT_SUSPENDED_WATCHDOG,
            #            VIR_DOMAIN_EVENT_SUSPENDED_RESTORED,
            #            VIR_DOMAIN_EVENT_SUSPENDED_FROM_SNAPSHOT
            VIR_DOMAIN_EVENT_SUSPENDED_API_ERROR
        ),
        #        VIR_DOMAIN_EVENT_RESUMED:
        #        (
        #            VIR_DOMAIN_EVENT_RESUMED_UNPAUSED,
        #            VIR_DOMAIN_EVENT_RESUMED_MIGRATED,
        #            VIR_DOMAIN_EVENT_RESUMED_FROM_SNAPSHOT
        #        ),
        VIR_DOMAIN_EVENT_STOPPED:
        (
            VIR_DOMAIN_EVENT_STOPPED_SHUTDOWN,
            VIR_DOMAIN_EVENT_STOPPED_DESTROYED,
            #            VIR_DOMAIN_EVENT_STOPPED_CRASHED,
            #            VIR_DOMAIN_EVENT_STOPPED_MIGRATED,
            #            VIR_DOMAIN_EVENT_STOPPED_SAVED,
            VIR_DOMAIN_EVENT_STOPPED_FAILED,
            #            VIR_DOMAIN_EVENT_STOPPED_FROM_SNAPSHOT
        ),
        VIR_DOMAIN_EVENT_SHUTDOWN:
        (
            VIR_DOMAIN_EVENT_SHUTDOWN_FINISHED,
        )
    },
    VIR_DOMAIN_EVENT_ID_REBOOT: {DUMMY: (DUMMY,)},
    #    VIR_DOMAIN_EVENT_ID_RTC_CHANGE: { DUMMY: ( DUMMY,) }
    VIR_DOMAIN_EVENT_ID_WATCHDOG:
    {
        VIR_DOMAIN_EVENT_WATCHDOG_NONE:     (DUMMY,),
        VIR_DOMAIN_EVENT_WATCHDOG_PAUSE:    (DUMMY,),
        VIR_DOMAIN_EVENT_WATCHDOG_RESET:    (DUMMY,),
        VIR_DOMAIN_EVENT_WATCHDOG_POWEROFF: (DUMMY,),
        VIR_DOMAIN_EVENT_WATCHDOG_SHUTDOWN: (DUMMY,),
        VIR_DOMAIN_EVENT_WATCHDOG_DEBUG: (DUMMY,)
    },
    VIR_DOMAIN_EVENT_ID_IO_ERROR:
    {
        VIR_DOMAIN_EVENT_IO_ERROR_NONE:   (DUMMY,),
        VIR_DOMAIN_EVENT_IO_ERROR_PAUSE:  (DUMMY,),
        VIR_DOMAIN_EVENT_IO_ERROR_REPORT: (DUMMY,)
    },
    #    VIR_DOMAIN_EVENT_ID_GRAPHICS:
    #    {
    #        DUMMY:
    #        (
    #            VIR_DOMAIN_EVENT_GRAPHICS_CONNECT,
    #            VIR_DOMAIN_EVENT_GRAPHICS_INITIALIZE,
    #            VIR_DOMAIN_EVENT_GRAPHICS_DISCONNECT
    #        )
    #    },
    VIR_DOMAIN_EVENT_ID_IO_ERROR_REASON: {DUMMY: (DUMMY,)},
    VIR_DOMAIN_EVENT_ID_CONTROL_ERROR: {DUMMY: (DUMMY,)}

}
