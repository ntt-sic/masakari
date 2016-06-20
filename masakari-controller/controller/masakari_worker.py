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
import traceback
import sys
import json
import datetime
# import masakari_config as config
import masakari_util as util
import os
from eventlet import greenthread
parentdir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                         os.path.pardir))
# rootdir = os.path.abspath(os.path.join(parentdir, os.path.pardir))
# project root directory needs to be add at list head rather than tail
# this file named 'masakari' conflicts to the directory name
if parentdir not in sys.path:
    sys.path = [parentdir] + sys.path

import db.api as dbapi
from oslo_log import log as logging

LOG = logging.getLogger(__name__)

class RecoveryControllerWorker(object):

    """
    RecoveryControllerWorker class:
    Execute VM recovery process.
    """

    def __init__(self, config_object):
        self.rc_config = config_object
        self.rc_util = util.RecoveryControllerUtil(self.rc_config)

        msg = ("BEGIN __init__: " \
               "parameters (config_object=%s)" % (config_object))
        LOG.debug(self.rc_util.msg_with_thread_id(msg))

        self.rc_util_db = util.RecoveryControllerUtilDb(self.rc_config)
        self.rc_util_api = util.RecoveryControllerUtilApi(self.rc_config)

        self.STATUS_NORMAL = 0
        self.STATUS_ERROR = 1

#        self.WAIT_SYNC_TIME_SEC = 60

        msg = "END __init__"
        LOG.debug(self.rc_util.msg_with_thread_id(msg))

    def _get_vm_param(self, uuid):

        try:
            msg = ("BEGIN _get_vm_param: " \
                   "parameters (uuid=%s)" % (uuid))
            LOG.debug(self.rc_util.msg_with_thread_id(msg))

            # Initalize return values.
            conf_dic = self.rc_config.get_value('recover_starter')
            api_max_retry_cnt = conf_dic.get('api_max_retry_cnt')
            api_retry_interval = conf_dic.get('api_retry_interval')
            cnt = 0
            while cnt < int(api_max_retry_cnt) + 1:
                try:
                    # Call nova show API.
                    server = self.rc_util_api.do_instance_show(uuid)

                    msg = ("END _get_vm_param: " \
                           "return %s" % (server))
                    LOG.debug(self.rc_util.msg_with_thread_id(msg))

                    return server
                except Exception:
                    if cnt == int(api_max_retry_cnt):
                        raise EnvironmentError("Failed to nova show API.")
                    else:
                        msg = (" Retry nova show API.")
                        LOG.info(self.rc_util.msg_with_thread_id(msg))
                        greenthread.sleep(int(api_retry_interval))
                        cnt += 1

            msg = "END _get_vm_param"
            LOG.debug(self.rc_util.msg_with_thread_id(msg))

        except EnvironmentError:
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(self.rc_util.msg_with_thread_id(error_type))
            LOG.error(self.rc_util.msg_with_thread_id(error_value))
            for tb in tb_list:
                LOG.error(self.rc_util.msg_with_thread_id(tb))
            raise EnvironmentError
        except KeyError:
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(self.rc_util.msg_with_thread_id(error_type))
            LOG.error(self.rc_util.msg_with_thread_id(error_value))
            for tb in tb_list:
                LOG.error(self.rc_util.msg_with_thread_id(tb))
            raise KeyError
        except:
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(self.rc_util.msg_with_thread_id(error_type))
            LOG.error(self.rc_util.msg_with_thread_id(error_value))
            for tb in tb_list:
                LOG.error(self.rc_util.msg_with_thread_id(tb))
            raise

    def _get_vmha_param(self, session, uuid, primary_id):
        # TODO(sampath): remove unused 'uuid' form args
        try:
            msg = ("BEGIN _get_vmha_param: " \
                   "parameters (session=%s, uuid=%s, primary_id=%s)" \
                % (session, uuid, primary_id))
            LOG.debug(self.rc_util.msg_with_thread_id(msg))

            msg = "Do get_vm_list_by_id."
            LOG.info(self.rc_util.msg_with_thread_id(msg))
            recover_data = dbapi.get_vm_list_by_id(session, primary_id)
            msg = "Succeeded in get_vm_list_by_id. " \
                + "Return_value = " + str(recover_data)
            LOG.info(self.rc_util.msg_with_thread_id(msg))

            if recover_data is None:
                raise EnvironmentError("Failed to recovery info.")

            # Set return values.
            recover_by = recover_data.recover_by
            recover_to = recover_data.recover_to

        except EnvironmentError:
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(self.rc_util.msg_with_thread_id(error_type))
            LOG.error(self.rc_util.msg_with_thread_id(error_value))
            for tb in tb_list:
                LOG.error(self.rc_util.msg_with_thread_id(tb))
            raise EnvironmentError
        except KeyError:
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(self.rc_util.msg_with_thread_id(error_type))
            LOG.error(self.rc_util.msg_with_thread_id(error_value))
            for tb in tb_list:
                LOG.error(self.rc_util.msg_with_thread_id(tb))
            raise KeyError
        except:
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(self.rc_util.msg_with_thread_id(error_type))
            LOG.error(self.rc_util.msg_with_thread_id(error_value))
            for tb in tb_list:
                LOG.error(self.rc_util.msg_with_thread_id(tb))
            raise

        msg = ("END _get_vmha_param: " \
               "return %s, %s" % (recover_by, recover_to))
        LOG.debug(self.rc_util.msg_with_thread_id(msg))

        return recover_by, recover_to

    def _execute_recovery(self, session, uuid, vm_state, HA_Enabled,
                          recover_by, recover_to):

        msg = ("BEGIN _execute_recovery: " \
               "parameters (session=%s, uuid=%s, " \
               "vm_state=%s, HA_Enabled=%s" \
               "recover_by=%s, recover_to=%s)" \
               % (session, uuid, vm_state, HA_Enabled, \
                  recover_by, recover_to))
        LOG.debug(self.rc_util.msg_with_thread_id(msg))

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
                    msg = "Inapplicable vm. instance_uuid = '%s', " \
                          "vm_state = '%s'" % (uuid, vm_state)
                    LOG.info(self.rc_util.msg_with_thread_id(msg))

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

        msg = ("END _execute_recovery: " \
               "return %s" % (res))
        LOG.debug(self.rc_util.msg_with_thread_id(msg))

        return res

    def _do_node_accident_vm_recovery(self, uuid, vm_state, evacuate_node):

        try:
            msg = ("BEGIN _do_node_accident_vm_recovery: " \
                   "parameters (uuid=%s, vm_state=%s, evacuate_node=%s)" \
                   % (uuid, vm_state, evacuate_node))
            LOG.debug(self.rc_util.msg_with_thread_id(msg))

            # Initalize status.
            status = self.STATUS_NORMAL

            # Evacuate API only evacuates an instance in active, stop or error
            # state. If an instance is in resized status, masakari resets the
            # instance state to *error* to evacuate it.
            if vm_state == 'resized':
                self.rc_util_api.do_instance_reset(uuid, 'error')

            self.rc_util_api.do_instance_evacuate(uuid, evacuate_node)

        except EnvironmentError:
            status = self.STATUS_ERROR
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(self.rc_util.msg_with_thread_id(error_type))
            LOG.error(self.rc_util.msg_with_thread_id(error_value))
            for tb in tb_list:
                LOG.error(self.rc_util.msg_with_thread_id(tb))
        except KeyError:
            status = self.STATUS_ERROR
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(self.rc_util.msg_with_thread_id(error_type))
            LOG.error(self.rc_util.msg_with_thread_id(error_value))
            for tb in tb_list:
                LOG.error(self.rc_util.msg_with_thread_id(tb))
        except ValueError:
            status = self.STATUS_ERROR
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(self.rc_util.msg_with_thread_id(error_type))
            LOG.error(self.rc_util.msg_with_thread_id(error_value))
            for tb in tb_list:
                LOG.error(self.rc_util.msg_with_thread_id(tb))
        except:
            status = self.STATUS_ERROR
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(self.rc_util.msg_with_thread_id(error_type))
            LOG.error(self.rc_util.msg_with_thread_id(error_value))
            for tb in tb_list:
                LOG.error(self.rc_util.msg_with_thread_id(tb))

        msg = ("END _do_node_accident_vm_recovery: " \
               "return %s" % (status))
        LOG.debug(self.rc_util.msg_with_thread_id(msg))

        return status

    def _skip_node_accident_vm_recovery(self, uuid, vm_state):
        msg = ("BEGIN _skip_node_accident_vm_recovery: " \
               "parameters (uuid=%s, vm_state=%s)" \
               % (uuid, vm_state))
        LOG.debug(self.rc_util.msg_with_thread_id(msg))

        # Initalize status.
        status = self.STATUS_NORMAL

        try:
            self.rc_util_api.do_instance_reset(uuid, 'error')

            msg = "Skipped recovery. " \
                  "instance_id:%s, " \
                  "accident type: [node accident]." % (uuid)
            LOG.info(self.rc_util.msg_with_thread_id(msg))

        except EnvironmentError:
            status = self.STATUS_ERROR
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(self.rc_util.msg_with_thread_id(error_type))
            LOG.error(self.rc_util.msg_with_thread_id(error_value))
            for tb in tb_list:
                LOG.error(self.rc_util.msg_with_thread_id(tb))
        except:
            status = self.STATUS_ERROR
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(self.rc_util.msg_with_thread_id(error_type))
            LOG.error(self.rc_util.msg_with_thread_id(error_value))
            for tb in tb_list:
                LOG.error(self.rc_util.msg_with_thread_id(tb))

        msg = ("END _skip_node_accident_vm_recovery: " \
               "return %s" % (status))
        LOG.debug(self.rc_util.msg_with_thread_id(msg))

        return status

    def _do_process_accident_vm_recovery(self, uuid, vm_state):
        msg = ("BEGIN _do_process_accident_vm_recovery: " \
               "parameters (uuid=%s, vm_state=%s)" \
               % (uuid, vm_state))
        LOG.debug(self.rc_util.msg_with_thread_id(msg))

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
            status = self.STATUS_ERROR
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(self.rc_util.msg_with_thread_id(error_type))
            LOG.error(self.rc_util.msg_with_thread_id(error_value))
            for tb in tb_list:
                LOG.error(self.rc_util.msg_with_thread_id(tb))
        except:
            status = self.STATUS_ERROR
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(self.rc_util.msg_with_thread_id(error_type))
            LOG.error(self.rc_util.msg_with_thread_id(error_value))
            for tb in tb_list:
                LOG.error(self.rc_util.msg_with_thread_id(tb))

        msg = ("END _do_process_accident_vm_recovery: " \
               "return %s" % (status))
        LOG.debug(self.rc_util.msg_with_thread_id(msg))

        return status

    def _skip_process_accident_vm_recovery(self, uuid, vm_state):
        msg = ("BEGIN _skip_process_accident_vm_recovery: " \
               "parameters (uuid=%s, vm_state=%s)" \
               % (uuid, vm_state))
        LOG.debug(self.rc_util.msg_with_thread_id(msg))

        # Initalize status.
        status = self.STATUS_NORMAL

        try:
            self.rc_util_api.do_instance_reset(uuid, 'error')

            # Call nova stop API.
            self.rc_util_api.do_instance_stop(uuid)

            msg = ("Skipped recovery. instance_id:%s, "
                    "accident type: [qemu process accident]." % uuid)
            LOG.info(self.rc_util.msg_with_thread_id(msg))

        except EnvironmentError:
            status = self.STATUS_ERROR
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(self.rc_util.msg_with_thread_id(error_type))
            LOG.error(self.rc_util.msg_with_thread_id(error_value))
            for tb in tb_list:
                LOG.error(self.rc_util.msg_with_thread_id(tb))
        except:
            status = self.STATUS_ERROR
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(self.rc_util.msg_with_thread_id(error_type))
            LOG.error(self.rc_util.msg_with_thread_id(error_value))
            for tb in tb_list:
                LOG.error(self.rc_util.msg_with_thread_id(tb))

        msg = ("END _skip_process_accident_vm_recovery: " \
               "return %s" % (status))
        LOG.debug(self.rc_util.msg_with_thread_id(msg))

        return status

    def host_maintenance_mode(self, notification_id, hostname,
                              update_progress):
        """
           nova-compute service change to disable or enable.
           :param notification_id: Notification ID included in the notification
           :param hostname: Host name of brocade target
        """
        try:
            msg = ("BEGIN host_maintenance_mode: " \
                   "parameters (notification_id=%s, hostname=%s, " \
                   "update_progress=%s)" \
                   % (notification_id, hostname, update_progress))
            LOG.debug(self.rc_util.msg_with_thread_id(msg))

            db_engine = dbapi.get_engine()
            session = dbapi.get_session(db_engine)
            self.rc_util_api.disable_host_status(hostname)

            if update_progress is True:
                self.rc_util_db.update_notification_list_db(
                    session,
                    'progress', 2, notification_id)

            msg = "END host_maintenance_mode"
            LOG.debug(self.rc_util.msg_with_thread_id(msg))

        except KeyError:
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(self.rc_util.msg_with_thread_id(error_type))
            LOG.error(self.rc_util.msg_with_thread_id(error_value))
            for tb in tb_list:
                LOG.error(self.rc_util.msg_with_thread_id(tb))
            return
        except:
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(self.rc_util.msg_with_thread_id(error_type))
            LOG.error(self.rc_util.msg_with_thread_id(error_value))
            for tb in tb_list:
                LOG.error(self.rc_util.msg_with_thread_id(tb))
            return

    def recovery_instance(self, uuid, primary_id, sem):
        """
           Execute VM recovery.
           :param uuid: Recovery target VM UUID
           :param primary_id: Unique ID of the vm_list table
           :param sem: Semaphore
        """
        try:
            msg = ("BEGIN methodname: " \
                   "parameters (uuid=%s, primary_id=%s, " \
                   "sem=%s)" % (uuid, primary_id, sem))
            LOG.debug(self.rc_util.msg_with_thread_id(msg))

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
            status = self.STATUS_ERROR
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(self.rc_util.msg_with_thread_id(error_type))
            LOG.error(self.rc_util.msg_with_thread_id(error_value))
            for tb in tb_list:
                LOG.error(self.rc_util.msg_with_thread_id(tb))
            return
        except KeyError:
            status = self.STATUS_ERROR
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(self.rc_util.msg_with_thread_id(error_type))
            LOG.error(self.rc_util.msg_with_thread_id(error_value))
            for tb in tb_list:
                LOG.error(self.rc_util.msg_with_thread_id(tb))
            return
        except:
            status = self.STATUS_ERROR
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(self.rc_util.msg_with_thread_id(error_type))
            LOG.error(self.rc_util.msg_with_thread_id(error_value))
            for tb in tb_list:
                LOG.error(self.rc_util.msg_with_thread_id(tb))
            return
        finally:
            try:
                # Successful execution.
                if status == self.STATUS_NORMAL:
                    self.rc_util_db.update_vm_list_db(
                        session, 'progress', 2, primary_id)

                    msg = "Recovery process has been completed successfully."
                    LOG.info(self.rc_util.msg_with_thread_id(msg))

                # Abnormal termination.
                else:
                    self.rc_util_db.update_vm_list_db(
                        session, 'progress', 3, primary_id)

                    msg = "Recovery process has been terminated abnormally."
                    LOG.info(self.rc_util.msg_with_thread_id(msg))

                # Release semaphore
                if sem:
                    sem.release()

                msg = "END recovery_instance"
                LOG.debug(self.rc_util.msg_with_thread_id(msg))

            except:
                error_type, error_value, traceback_ = sys.exc_info()
                tb_list = traceback.format_tb(traceback_)
                LOG.error(self.rc_util.msg_with_thread_id(error_type))
                LOG.error(self.rc_util.msg_with_thread_id(error_value))
                for tb in tb_list:
                    LOG.error(self.rc_util.msg_with_thread_id(tb))
                return
