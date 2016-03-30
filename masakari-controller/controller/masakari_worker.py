#!/usr/bin/env python
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

"""
This file defines RecoveryControllerWorker class.
"""

import ConfigParser
import syslog
import traceback
import sys
import json
import datetime
from eventlet import greenthread
# import masakari_config as config
import masakari_util as util
import os
parentdir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                         os.path.pardir))
# rootdir = os.path.abspath(os.path.join(parentdir, os.path.pardir))
# project root directory needs to be add at list head rather than tail
# this file named 'masakari' conflicts to the directory name
if parentdir not in sys.path:
    sys.path = [parentdir] + sys.path

import db.api as dbapi


class RecoveryControllerWorker(object):

    """
    RecoveryControllerWorker class:
    Execute VM recovery process.
    """

    def __init__(self, config_object):
        self.rc_config = config_object
        self.rc_util = util.RecoveryControllerUtil(self.rc_config)
        self.rc_util_db = util.RecoveryControllerUtilDb(self.rc_config)
        self.rc_util_api = util.RecoveryControllerUtilApi(self.rc_config)

        self.STATUS_NORMAL = 0
        self.STATUS_ERROR = 1

#        self.WAIT_SYNC_TIME_SEC = 60

    def _get_vm_param(self, uuid):

        try:
            # Initalize return values.
            conf_dic = self.rc_config.get_value('recover_starter')
            api_max_retry_cnt = conf_dic.get('api_max_retry_cnt')
            api_retry_interval = conf_dic.get('api_retry_interval')
            cnt = 0
            while cnt < int(api_max_retry_cnt) + 1:
                try:
                    # Call nova show API.
                    server = self.rc_util_api.do_instance_show(uuid)
                    return server
                except Exception:
                    if cnt == int(api_max_retry_cnt):
                        raise EnvironmentError("Failed to nova show API.")
                    else:
                        msg = ("[RecoveryControllerWorker_0040]"
                               " Retry nova show API.")
                        self.rc_util.syslogout(msg, syslog.LOG_INFO)
                        greenthread.sleep(int(api_retry_interval))
                        cnt += 1

        except EnvironmentError:
            self.rc_util.syslogout_ex("RecoveryControllerWorker_0004",
                                      syslog.LOG_ERR)
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            raise EnvironmentError
        except KeyError:
            self.rc_util.syslogout_ex("RecoveryControllerWorker_0005",
                                      syslog.LOG_ERR)
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            raise KeyError
        except:
            self.rc_util.syslogout_ex("RecoveryControllerWorker_0006",
                                      syslog.LOG_ERR)
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            raise

    def _get_vmha_param(self, session, uuid, primary_id):
        # TODO(sampath): remove unused 'uuid' form args
        try:
            recover_data = dbapi.get_vm_list_by_id(session, primary_id)

            if recover_data is None:
                raise EnvironmentError("Failed to recovery info.")

            # Set return values.
            recover_by = recover_data.recover_by
            recover_to = recover_data.recover_to

        except EnvironmentError:
            self.rc_util.syslogout_ex("RecoveryControllerWorker_0007",
                                      syslog.LOG_ERR)
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            raise EnvironmentError
        except KeyError:
            self.rc_util.syslogout_ex("RecoveryControllerWorker_0008",
                                      syslog.LOG_ERR)
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            raise KeyError
        except:
            self.rc_util.syslogout_ex("RecoveryControllerWorker_0010",
                                      syslog.LOG_ERR)
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            raise

        return recover_by, recover_to

    def _execute_recovery(self, session, uuid, vm_state, HA_Enabled,
                          recover_by, recover_to):

        # Initalize status.
        res = self.STATUS_NORMAL

        # For node accident.
        # TODO(masa) Change value of recover_by to human readable string.
        # In current implementation,
        # recover_by == 0: host (hypervisor) goes down
        # recover_by == 1: virtual machine intance goes down
        if recover_by == 0:
            if HA_Enabled == 'ON':
                if vm_state == 'active' or \
                        vm_state == 'stopped' or \
                        vm_state == 'resized':
                    res = self._do_node_accident_vm_recovery(
                        uuid, vm_state, recover_to)
                else:
                    self.rc_util.syslogout_ex("RecoveryControllerWorker_0041",
                                              syslog.LOG_INFO)
                    msg = "Inapplicable vm. instance_uuid = '%s', " \
                          "vm_state = '%s'" % (uuid, vm_state)
                    self.rc_util.syslogout(msg, syslog.LOG_INFO)

            elif HA_Enabled == 'OFF':
                res = self._skip_node_accident_vm_recovery(
                    uuid, vm_state)

        # For vm accident.
        elif recover_by == 1:
            if HA_Enabled == 'ON':
                res = self._do_process_accident_vm_recovery(
                    uuid, vm_state)

            elif HA_Enabled == 'OFF':
                res = self._skip_process_accident_vm_recovery(
                    uuid, vm_state)

        return res

    def _do_node_accident_vm_recovery(self, uuid, vm_state, evacuate_node):

        try:
            # Initalize status.
            status = self.STATUS_NORMAL

            # Evacuate API only evacuates an instance in active, stop or error
            # state. If an instance is in resized status, masakari resets the
            # instance state to *error* to evacuate it.
            if vm_state == 'resized':
                self.rc_util_api.do_instance_reset(uuid, 'error')

            self.rc_util_api.do_instance_evacuate(uuid, evacuate_node)

        except EnvironmentError:
            self.rc_util.syslogout_ex("RecoveryControllerWorker_0013",
                                      syslog.LOG_ERR)
            status = self.STATUS_ERROR
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
        except KeyError:
            self.rc_util.syslogout_ex("RecoveryControllerWorker_0015",
                                      syslog.LOG_ERR)
            status = self.STATUS_ERROR
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
        except ValueError:
            self.rc_util.syslogout_ex("RecoveryControllerWorker_0012",
                                      syslog.LOG_ERR)
            status = self.STATUS_ERROR
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
        except:
            self.rc_util.syslogout_ex("RecoveryControllerWorker_0016",
                                      syslog.LOG_ERR)
            status = self.STATUS_ERROR
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)

        return status

    def _skip_node_accident_vm_recovery(self, uuid, vm_state):

        # Initalize status.
        status = self.STATUS_NORMAL

        try:
            self.rc_util_api.do_instance_reset(uuid, 'error')

            self.rc_util.syslogout_ex("RecoveryControllerWorker_0017",
                                      syslog.LOG_INFO)
            msg = "Skipped recovery. " \
                  "instance_id:%s, " \
                  "accident type: [node accident]." % (uuid)
            self.rc_util.syslogout(msg, syslog.LOG_INFO)

        except EnvironmentError:
            self.rc_util.syslogout_ex("RecoveryControllerWorker_0018",
                                      syslog.LOG_ERR)
            status = self.STATUS_ERROR
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
        except:
            self.rc_util.syslogout_ex("RecoveryControllerWorker_0019",
                                      syslog.LOG_ERR)
            status = self.STATUS_ERROR
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)

        return status

    def _do_process_accident_vm_recovery(self, uuid, vm_state):

        # Initalize status.
        status = self.STATUS_NORMAL

        try:
            # Idealy speaking, an instance fail notification isn't sent
            # from instancemonitor if the instance is in stopped state
            # since there is no instance on the hypervisor. However,
            # in some race conditions, it could happen.
            if vm_state == 'stopped':
                self.rc_util_api.do_instance_reset(uuid, 'stopped')
                return status

            if vm_state == 'resized':
                self.rc_util_api.do_instance_reset(uuid, 'active')

            self.rc_util_api.do_instance_stop(uuid)

            # Wait to be in the Stopped.
            conf_dic = self.rc_config.get_value('recover_starter')
            api_check_interval = conf_dic.get('api_check_interval')
            api_check_max_cnt = conf_dic.get('api_check_max_cnt')
            loop_cnt = 0

            while loop_cnt < int(api_check_max_cnt):
                vm_info = self._get_vm_param(uuid)
                vm_state = getattr(vm_info, 'OS-EXT-STS:vm_state')
                if vm_state == 'stopped':
                    break
                else:
                    loop_cnt += 1
                    greenthread.sleep(int(api_check_interval))

            if loop_cnt == int(api_check_max_cnt):
                msg = "vm_state did not become stopped."
                raise EnvironmentError(msg)

            self.rc_util_api.do_instance_start(uuid)

        except EnvironmentError:
            self.rc_util.syslogout_ex("RecoveryControllerWorker_0020",
                                      syslog.LOG_ERR)
            status = self.STATUS_ERROR
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
        except:
            self.rc_util.syslogout_ex("RecoveryControllerWorker_0021",
                                      syslog.LOG_ERR)
            status = self.STATUS_ERROR
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)

        return status

    def _skip_process_accident_vm_recovery(self, uuid, vm_state):

        # Initalize status.
        status = self.STATUS_NORMAL

        try:
            self.rc_util_api.do_instance_reset(uuid, 'error')

            # Call nova stop API.
            self.rc_util_api.do_instance_stop(uuid)

            msg = "[RecoveryControllerWorker_0022]"
            msg += ("Skipped recovery. instance_id:%s, "
                    "accident type: [qemu process accident]." % uuid)
            self.rc_util.syslogout(msg, syslog.LOG_INFO)

        except EnvironmentError:
            self.rc_util.syslogout_ex("RecoveryControllerWorker_0023",
                                      syslog.LOG_ERR)
            status = self.STATUS_ERROR
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
        except:
            self.rc_util.syslogout_ex("RecoveryControllerWorker_0024",
                                      syslog.LOG_ERR)
            status = self.STATUS_ERROR
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)

        return status

    def host_maintenance_mode(self, notification_id, hostname,
                              update_progress):
        """
           nova-compute service change to disable or enable.
           :param notification_id: Notification ID included in the notification
           :param hostname: Host name of brocade target
        """
        try:
            db_engine = dbapi.get_engine()
            session = dbapi.get_session(db_engine)
            self.rc_util_api.disable_host_status(hostname)

            if update_progress is True:
                self.rc_util_db.update_notification_list_db(
                    session,
                    'progress', 2, notification_id)

        except KeyError:
            self.rc_util.syslogout_ex("RecoveryControllerWorker_0031",
                                      syslog.LOG_ERR)
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            return
        except:
            self.rc_util.syslogout_ex("RecoveryControllerWorker_0032",
                                      syslog.LOG_ERR)
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            return

    def recovery_instance(self, uuid, primary_id, sem):
        """
           Execute VM recovery.
           :param uuid: Recovery target VM UUID
           :param primary_id: Unique ID of the vm_list table
           :param sem: Semaphore
        """
        try:
            sem.acquire()
            db_engine = dbapi.get_engine()
            session = dbapi.get_session(db_engine)

            # Initlize status.
            status = self.STATUS_NORMAL

            # Update vmha recovery status.
            self.rc_util_db.update_vm_list_db(
                session, 'progress', 1, primary_id)

            # Get vm infomation.
            vm_info = self._get_vm_param(uuid)
            HA_Enabled = vm_info.metadata.get('HA-Enabled')
            if HA_Enabled:
                HA_Enabled = HA_Enabled.upper()
            if HA_Enabled != 'OFF':
                HA_Enabled = 'ON'

            # Set recovery parameter.
            exe_param = {}
            exe_param['vm_state'] = getattr(vm_info, 'OS-EXT-STS:vm_state')
            exe_param['HA-Enabled'] = HA_Enabled
            recover_by, recover_to = self._get_vmha_param(
                session, uuid, primary_id)
            exe_param['recover_by'] = recover_by
            exe_param['recover_to'] = recover_to

            # Execute.
            status = self._execute_recovery(session,
                                            uuid,
                                            exe_param.get("vm_state"),
                                            exe_param.get("HA-Enabled"),
                                            exe_param.get("recover_by"),
                                            exe_param.get("recover_to"))

        except EnvironmentError:
            self.rc_util.syslogout_ex("RecoveryControllerWorker_0034",
                                      syslog.LOG_ERR)
            status = self.STATUS_ERROR
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            return
        except KeyError:
            self.rc_util.syslogout_ex("RecoveryControllerWorker_0035",
                                      syslog.LOG_ERR)
            status = self.STATUS_ERROR
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            return
        except:
            self.rc_util.syslogout_ex("RecoveryControllerWorker_0037",
                                      syslog.LOG_ERR)
            status = self.STATUS_ERROR
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            return
        finally:
            try:
                # Successful execution.
                if status == self.STATUS_NORMAL:
                    self.rc_util_db.update_vm_list_db(
                        session, 'progress', 2, primary_id)

                # Abnormal termination.
                else:
                    self.rc_util_db.update_vm_list_db(
                        session, 'progress', 3, primary_id)

                # Release semaphore
                if sem:
                    sem.release()
            except:
                self.rc_util.syslogout_ex("RecoveryControllerWorker_0039",
                                          syslog.LOG_ERR)
                error_type, error_value, traceback_ = sys.exc_info()
                tb_list = traceback.format_tb(traceback_)
                self.rc_util.syslogout(error_type, syslog.LOG_ERR)
                self.rc_util.syslogout(error_value, syslog.LOG_ERR)
                for tb in tb_list:
                    self.rc_util.syslogout(tb, syslog.LOG_ERR)
                return
