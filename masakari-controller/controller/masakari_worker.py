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
import MySQLdb
import syslog
import traceback
import sys
import json
import datetime
from eventlet import greenthread
# TODO(sampath):
# Delete this import if unused
# conficlt with _do_action_db(self, config, sql):
#import masakari_config as config
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
                # Call nova show API.
                rc, rbody = self.rc_util_api.do_instance_show(uuid)
                rbody = json.loads(rbody)

                if rc == '200':
                    break
                elif rc == '500':
                    if cnt == int(api_max_retry_cnt):
                        raise EnvironmentError("Failed to nova show API.")
                    else:
                        self.rc_util.syslogout_ex(
                            "RecoveryControllerWorker_0040", syslog.LOG_INFO)
                        msg = "Retry nova show API."
                        self.rc_util.syslogout(msg, syslog.LOG_INFO)
                        greenthread.sleep(int(api_retry_interval))
                else:
                    raise EnvironmentError("Failed to nova show API.")
                cnt += 1

            # Set return values.
            vm_info = rbody.get('server')

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

        return vm_info

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
        if recover_by == 0:
            if HA_Enabled == 'ON':
                if vm_state == 'active' or \
                        vm_state == 'stopped' or \
                        vm_state == 'resized':
                    res = self._do_node_accident_vm_recovery(
                        session,
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

    def _do_node_accident_vm_recovery(self, session,
                                      uuid, vm_state, evacuate_node):

        try:
            # Initalize status.
            status = self.STATUS_NORMAL

            # Preparation recovery.
            rc, rbody = self.rc_util_api.do_instance_reset(uuid, 'error')
            if rc != '202':
                rbody = json.loads(rbody)
                msg = '%s(code:%s)' % (rbody.get('error').get(
                    'message'), rbody.get('error').get('code'))
                raise EnvironmentError(msg)

            if vm_state == 'resized':
                old_vm_state = self._select_old_vm_state(uuid)
                if old_vm_state == 'stopped':
                    # To change the vm_state to match the old_vm_state.
                    self._update_vm_state(uuid, old_vm_state)

                elif old_vm_state == 'active':
                    # Consider AutoRecoverFlag ON. do nothing.
                    self.rc_util.syslogout_ex("RecoveryControllerWorker_0011",
                                              syslog.LOG_INFO)
                    msg = "Consider AutoRecoverFlag ON."
                    self.rc_util.syslogout(msg, syslog.LOG_INFO)
                else:
                    # Unexpected record.
                    msg = "Do Nothing because select " \
                          "instance_system_metadata result is unexpected."
                    raise ValueError(msg)
            elif vm_state == 'stopped':
                self._update_vm_state(uuid, vm_state)

            # Check task_state(Call nova show API).
            vm_info = self._get_vm_param(uuid)
            task_state = vm_info.get('OS-EXT-STS:task_state')

            # It wants to record the task_state in the log.
            msg = "%s of the tas_state is %s." % (uuid, task_state)
            self.rc_util.syslogout_ex("RecoveryControllerWorker_0042",
                                      syslog.LOG_INFO)
            self.rc_util.syslogout_ex(msg, syslog.LOG_INFO)

            # Execute recovery(Call nova evacuate API).
            rc, rbody = self.rc_util_api.do_instance_evacuate(
                uuid, evacuate_node)

            if rc != '200':
                rbody = json.loads(rbody)
                msg = '%s(code:%s)' % (rbody.get('error').get(
                    'message'), rbody.get('error').get('code'))
                raise EnvironmentError(msg)

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
        except MySQLdb.Error:
            self.rc_util.syslogout_ex("RecoveryControllerWorker_0014",
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
            # Call nova reset-state API(do not wait for sync).
            rc, rbody = self.rc_util_api.do_instance_reset(uuid, 'error')
            if rc != '202':
                rbody = json.loads(rbody)
                msg = '%s(code:%s)' % (rbody.get('error').get(
                    'message'), rbody.get('error').get('code'))
                raise EnvironmentError(msg)

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
            # Call nova reset-state API.
            rc, rbody = self.rc_util_api.do_instance_reset(uuid, 'active')
            if rc != '202':
                rbody = json.loads(rbody)
                msg = '%s(code:%s)' % (rbody.get('error').get(
                    'message'), rbody.get('error').get('code'))
                raise EnvironmentError(msg)

            # Call nova stop API.
            rc, rbody = self.rc_util_api.do_instance_stop(uuid)
            if rc != '202' and rc != '409':
                rbody = json.loads(rbody)
                msg = '%s(code:%s)' % (rbody.get('error').get(
                    'message'), rbody.get('error').get('code'))
                raise EnvironmentError(msg)
            elif rc == '409':
                rbody = json.loads(rbody)
                return_message = rbody.get('conflictingRequest').get(
                    'message')

                ignore_message_list = []
                ignore_message_list.append(
                    "in vm_state stopped. "
                    "Cannot stop while the instance "
                    "is in this state.")
                # kilo message
                ignore_message_list.append(
                    "while it is in vm_state stopped")

                def msg_filter(return_message, ignore_message_list):
                    # TODO(sampath):
                    # Make this simple and opnestak version independet
                    # This patch is to absorb the message diff in juno and kilo
                    # juno message
                    for ignore_message in ignore_message_list:
                        if ignore_message in return_message:
                            return True
                    return False

                if not msg_filter(return_message, ignore_message_list):
                    msg = '%s(code:%s)' % (return_message, rc)
                    raise EnvironmentError(msg)

            # Wait to be in the Stopped.
            conf_dic = self.rc_config.get_value('recover_starter')
            api_check_interval = conf_dic.get('api_check_interval')
            api_check_max_cnt = conf_dic.get('api_check_max_cnt')
            loop_cnt = 0

            while loop_cnt < int(api_check_max_cnt):
                vm_info = self._get_vm_param(uuid)
                vm_state = vm_info.get('OS-EXT-STS:vm_state')
                if vm_state == 'stopped':
                    break
                else:
                    loop_cnt += 1
                    greenthread.sleep(int(api_check_interval))

            if loop_cnt == int(api_check_max_cnt):
                msg = "vm_state did not become stopped."
                raise EnvironmentError(msg)

                # Call nova start API.
            rc, rbody = self.rc_util_api.do_instance_start(uuid)

            if rc != '202' and rc != '409':
                rbody = json.loads(rbody)
                msg = '%s(code:%s)' % (rbody.get('error').get(
                    'message'), rbody.get('error').get('code'))
                raise EnvironmentError(msg)
            elif rc == '409':
                rbody = json.loads(rbody)
                return_message = rbody.get('conflictingRequest').get(
                    'message')
                ignore_message_list = []
                #  juno
                ignore_message_list.append(
                    "in vm_state active. "
                    "Cannot start while the instance "
                    "is in this state.")
                # kilo
                ignore_message_list.append(
                    "while it is in vm_state active")

                def msg_filter(return_message, ignore_message_list):
                    # TODO(sampath)
                    # see the previous comment for def msg_filter
                    for ignore_message in ignore_message_list:
                        if ignore_message in return_message:
                            return True
                    return False

                if not msg_filter(return_message, ignore_message_list):
                    msg = '%s(code:%s)' % (return_message, rc)
                    raise EnvironmentError(msg)

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
            # Call nova reset-state API.
            rc, rbody = self.rc_util_api.do_instance_reset(uuid, 'error')
            if rc != '202':
                rbody = json.loads(rbody)
                msg = '%s(code:%s)' % (rbody.get('error').get(
                    'message'), rbody.get('error').get('code'))
                raise EnvironmentError(msg)

            # Call nova stop API.
            rc, rbody = self.rc_util_api.do_instance_stop(uuid)
            if rc != '202' and rc != '409':
                rbody = json.loads(rbody)
                msg = '%s(code:%s)' % (rbody.get('error').get(
                    'message'), rbody.get('error').get('code'))
                raise EnvironmentError(msg)
            elif rc == '409':
                rbody = json.loads(rbody)
                return_message = rbody.get('conflictingRequest').get(
                    'message')

                ignore_message_list = []
                # juno
                ignore_message_list.append(
                    "in vm_state stopped. "
                    "Cannot stop while the instance "
                    "is in this state.")
                # kilo
                ignore_message_list.append(
                    "while it is in vm_state stopped")

                def msg_filter(return_message, ignore_message_list):
                    # TODO(sampath)
                    # see the previous comment for def msg_filter
                    for ignore_message in ignore_message_list:
                        if ignore_message in return_message:
                            return True
                    return False

                if not msg_filter(return_message, ignore_message_list):
                    msg = '%s(code:%s)' % (return_message, rc)
                    raise EnvironmentError(msg)

            self.rc_util.syslogout_ex("RecoveryControllerWorker_0022",
                                      syslog.LOG_INFO)
            msg = "Skipped recovery. " \
                  "instance_id:%s, " \
                  "accident type: [qemu process accident]." % (uuid)
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

    def _do_action_db(self, config, sql):
        # TODO(sampath)
        # Remove this method and use sqlalchemy
        result = None
        db = None
        cursor = None

        try:
            # Connect db
            db = MySQLdb.connect(host=config.get('host'),
                                 db=config.get('name'),
                                 user=config.get('user'),
                                 passwd=config.get('passwd'),
                                 charset=config.get('charset'))

            cursor = db.cursor(MySQLdb.cursors.DictCursor)

            # Excecute SQL
            cursor.execute(sql)

        except MySQLdb.Error:
            self.rc_util.syslogout_ex("RecoveryControllerWorker_0025",
                                      syslog.LOG_ERR)
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            raise MySQLdb.Error
        except KeyError:
            self.rc_util.syslogout_ex("RecoveryControllerWorker_0026",
                                      syslog.LOG_ERR)
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            raise KeyError
        except:
            self.rc_util.syslogout_ex("RecoveryControllerWorker_0027",
                                      syslog.LOG_ERR)
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            raise

        finally:
            if sql.find('SELECT') == 0:
                if cursor:
                    result = cursor.fetchone()
            else:
                if db:
                    db.commit()

            if cursor:
                cursor.close()
            if db:
                db.close()

        return result

    def _select_old_vm_state(self, uuid):
        conf_db_dic = self.rc_config.get_value('db')
        # Set target database.
        local_conf_dic = {}
        local_conf_dic['passwd'] = conf_db_dic['passwd']
        local_conf_dic['host'] = conf_db_dic['host']
        local_conf_dic['charset'] = conf_db_dic['charset']
        local_conf_dic['name'] = 'nova'
        local_conf_dic['user'] = conf_db_dic['user']

        sql = "SELECT value FROM instance_system_metadata " \
              "WHERE instance_uuid='%s' AND `key`='old_vm_state' " \
              "order by created_at desc limit 1" % (uuid)

        # Do sql.
        sql_result = self._do_action_db(local_conf_dic, sql)

        # Return old_vm_state.
        if sql_result:
            return sql_result.get('value')
        else:
            return None

    def _update_vm_state(self, uuid, vm_state):
        conf_db_dic = self.rc_config.get_value('db')
        # Set target database.
        local_conf_dic = {}
        local_conf_dic['passwd'] = conf_db_dic['passwd']
        local_conf_dic['host'] = conf_db_dic['host']
        local_conf_dic['charset'] = conf_db_dic['charset']
        local_conf_dic['name'] = 'nova'
        local_conf_dic['user'] = conf_db_dic['user']

        # Update instances table.
        # removed the task_state update to task_state=NULL from here
        updated_at = datetime.datetime.now()
        sql = "UPDATE instances SET vm_state='%s' , " \
              "updated_at='%s' " \
              "WHERE uuid='%s'" % (vm_state, updated_at, uuid)

        self.rc_util.syslogout_ex("RecoveryControllerWorker_0028",
                                  syslog.LOG_INFO)
        msg = "Updated vm_state column of instances table. "\
              "Query is \"%s\"" % sql
        self.rc_util.syslogout(msg, syslog.LOG_INFO)

        # Do sql.
        self._do_action_db(local_conf_dic, sql)

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
            rc, rbody = self.rc_util_api.do_host_maintenance_mode(hostname,
                                                                  'disable')
            if rc != '200':
                self.rc_util.syslogout_ex("RecoveryControllerWorker_0029",
                                          syslog.LOG_ERR)
                msg = "Failed to nova API. change to disable."
                self.rc_util.syslogout(msg, syslog.LOG_ERR)
                raise Exception(msg)

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
            HA_Enabled = vm_info.get('metadata').get('HA-Enabled')
            if HA_Enabled:
                HA_Enabled = HA_Enabled.upper()
            if HA_Enabled != 'OFF':
                HA_Enabled = 'ON'

            # Set recovery parameter.
            exe_param = {}
            exe_param['vm_state'] = vm_info.get('OS-EXT-STS:vm_state')
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
        except MySQLdb.Error:
            self.rc_util.syslogout_ex("RecoveryControllerWorker_0036",
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

            except MySQLdb.Error:
                self.rc_util.syslogout_ex("RecoveryControllerWorker_0038",
                                          syslog.LOG_ERR)
                error_type, error_value, traceback_ = sys.exc_info()
                tb_list = traceback.format_tb(traceback_)
                self.rc_util.syslogout(error_type, syslog.LOG_ERR)
                self.rc_util.syslogout(error_value, syslog.LOG_ERR)
                for tb in tb_list:
                    self.rc_util.syslogout(tb, syslog.LOG_ERR)
                return
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
