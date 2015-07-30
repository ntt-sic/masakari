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
This file defines the RecoveryControllerStarter class.
"""

import threading
import MySQLdb
import sys
import datetime
import ConfigParser
import threading
import syslog
import traceback
import json
# import RecoveryControllerWorker
# import RecoveryControllerConfig
# import RecoveryControllerUtil
import masakari_worker as worker
import masakari_config as config
import masakari_util as util
from eventlet import greenthread

class RecoveryControllerStarter(object):

    """
    RecoveryControllerStarter class:
    This class executes startup processing of VM Recover execution thread.
    """

    def __init__(self, config_object):
        """
        Constructor:
        This constructor creates RecoveryControllerUtil object,
        RecoveryControllerWorker object.
        """
        self.rc_config = config_object
        self.rc_worker = worker.RecoveryControllerWorker(config_object)
        self.rc_util = util.RecoveryControllerUtil(config_object)
        self.rc_util_db = util.RecoveryControllerUtilDb(config_object)
        self.rc_util_api = util.RecoveryControllerUtilApi(config_object)

    def _compare_timestamp(self, timestamp_1, timestamp_2):

        delta = timestamp_1 - timestamp_2
        return long(delta.total_seconds())

    def _create_vm_list_db_for_failed_instance(self,
                                               notification_id,
                                               notification_uuid):
        try:
            conf_db_dic = self.rc_config.get_value('db')
            conf_recover_starter_dic = self.rc_config.get_value(
                'recover_starter')

            interval_to_be_retry = conf_recover_starter_dic.get(
                "interval_to_be_retry")
            max_retry_cnt = conf_recover_starter_dic.get("max_retry_cnt")

            # Connect db
            db = MySQLdb.connect(host=conf_db_dic.get("host"),
                                 db=conf_db_dic.get("name"),
                                 user=conf_db_dic.get("user"),
                                 passwd=conf_db_dic.get("passwd"),
                                 charset=conf_db_dic.get("charset"))

            # Execute SQL
            cursor = db.cursor(MySQLdb.cursors.DictCursor)

            # check duplication
            row_cnt = cursor.execute(("SELECT progress, create_at, retry_cnt "
                                      "FROM vm_list "
                                      "WHERE uuid = '%s' "
                                      "ORDER BY create_at "
                                      "DESC LIMIT 1") % (notification_uuid))
            result = cursor.fetchone()
            cursor.close()
            db.close()

            # row_cnt is always 0 or 1
            if row_cnt == 0:
                self.rc_util_db.insert_vm_list_db(
                    notification_id, notification_uuid, 0)
                return 0
            else:
                result_progress = result.get("progress")
                result_create_at = result.get("create_at")
                result_retry_cnt = result.get("retry_cnt")

                delta = self._compare_timestamp(
                    datetime.datetime.now(), result_create_at)
                if result_progress == 2 and \
                delta <= long(interval_to_be_retry):
                    if result_retry_cnt < long(max_retry_cnt):
                        self.rc_util_db.insert_vm_list_db(
                            notification_id,
                            notification_uuid,
                            result_retry_cnt + 1)
                        return 0
                    else:
                        # Not insert vm_list db.
                        self.rc_util.syslogout_ex("RecoveryControllerStarter_0004",
                                                  syslog.LOG_INFO)
                        msg = "Do not insert a record" \
                        + " into vm_list db because retry_cnt about " \
                        + notification_uuid \
                        + " is over " \
                        + max_retry_cnt \
                        + " times."
                        self.rc_util.syslogout(msg, syslog.LOG_INFO)
                        return 1
                elif result_progress == 2 and \
                delta > long(interval_to_be_retry):
                    self.rc_util_db.insert_vm_list_db(
                        notification_id, notification_uuid, 0)
                    return 0
                else:
                    # Not insert vm_list db.
                    self.rc_util.syslogout_ex("RecoveryControllerStarter_0005",
                                              syslog.LOG_INFO)
                    msg = "Do not insert a record " \
                    + "into vm_list db because progress of " \
                    + notification_uuid \
                    + " is " \
                    + str(result_progress)
                    self.rc_util.syslogout(msg, syslog.LOG_INFO)
                    return 1

        except MySQLdb.Error:
            self.rc_util.syslogout_ex("RecoveryControllerStarter_0006",
                                      syslog.LOG_ERR)
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            raise MySQLdb.Error
        except KeyError:
            self.rc_util.syslogout_ex("RecoveryControllerStarter_0007",
                                      syslog.LOG_ERR)
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            raise KeyError

    def _create_vm_list_db_for_failed_host(self,
                                           notification_id,
                                           notification_uuid):
        try:
            conf_db_dic = self.rc_config.get_value('db')
            conf_recover_starter_dic = self.rc_config.get_value(
                'recover_starter')

            interval_to_be_retry = conf_recover_starter_dic.get(
                "interval_to_be_retry")
            max_retry_cnt = conf_recover_starter_dic.get("max_retry_cnt")

            # Connect db
            db = MySQLdb.connect(host=conf_db_dic.get("host"),
                                 db=conf_db_dic.get("name"),
                                 user=conf_db_dic.get("user"),
                                 passwd=conf_db_dic.get("passwd"),
                                 charset=conf_db_dic.get("charset"))

            # Execute SQL
            cursor = db.cursor(MySQLdb.cursors.DictCursor)

            # check duplication
            row_cnt = cursor.execute(("SELECT * FROM vm_list "
                                      "WHERE uuid = '%s' AND "
                                      "(progress = 0 OR progress = 1) "
                                      "ORDER BY create_at DESC LIMIT 1") % (notification_uuid))
            cursor.close()
            db.close()

            if row_cnt == 0:
                self.rc_util_db.insert_vm_list_db(
                    notification_id, notification_uuid, 0)
                return 0
            else:
                self.rc_util.syslogout_ex("RecoveryControllerStarter_0008",
                                          syslog.LOG_INFO)
                msg = "Do not insert a record into vm_list db " \
                      "because there are same uuid records that " \
                      "progress is 0 or 1."
                self.rc_util.syslogout(msg, syslog.LOG_INFO)
                return 1

        except MySQLdb.Error:
            self.rc_util.syslogout_ex("RecoveryControllerStarter_0009",
                                      syslog.LOG_ERR)
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            raise MySQLdb.Error
        except KeyError:
            self.rc_util.syslogout_ex("RecoveryControllerStarter_0010",
                                      syslog.LOG_ERR)
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            raise KeyError

    def add_failed_instance(self, notification_id, notification_uuid):
        """
        VM recover start thread :
            This thread starts the VM recover execution thread.
        :param notification_id: The notification ID included in the
         notification
        :param :notification_uuid: The recovery target VM UUID of which are
         included in the notification
        """

        try:
            ret = self._create_vm_list_db_for_failed_instance(
                notification_id, notification_uuid)

            # update record in notification_list
            self.rc_util_db.update_notification_list_db(
                'progress', 2, notification_id)

            # create semaphore (Multiplicity = 1)
            sem_recovery_instance = threading.Semaphore(1)
            # create and start thread
            if ret == 0:
                threading.Thread(target=self.rc_worker.recovery_instance, args=(
                    notification_uuid, sem_recovery_instance)).start()

            return

        except MySQLdb.Error:
            self.rc_util.syslogout_ex("RecoveryControllerStarter_0011",
                                      syslog.LOG_ERR)
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            return
        except KeyError:
            self.rc_util.syslogout_ex("RecoveryControllerStarter_0012",
                                      syslog.LOG_ERR)
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            return
        except:
            self.rc_util.syslogout_ex("RecoveryControllerStarter_0013",
                                      syslog.LOG_ERR)
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            return

    def add_failed_host(self,
                        notification_id,
                        notification_hostname,
                        notification_cluster_port,
                        retry_mode):
        """
        Node recover start thread :
            This thread starts the VM recover execution thread,
            only the number of existing vm in the recovery target node.
        :param notification_id: The notification ID included in the
         notification
        :param notification_hostname: The host name of the failure node that
         is included in the notification
        """

        try:
            conf_dict = self.rc_config.get_value('recover_starter')
            recovery_max_retry_cnt = conf_dict.get('recovery_max_retry_cnt')
            recovery_retry_interval = conf_dict.get('recovery_retry_interval')

            rc, rbody = self.rc_util_api.do_hypervisor_servers(
                notification_hostname)

            # Get vm_list from rbody
            vm_list = []
            rbody_dict = json.loads(rbody)
            hypervisors_list = rbody_dict.get("hypervisors")
            for i in range(0, len(hypervisors_list)):
                hypervisors_dict = hypervisors_list[i]
                servers_list = hypervisors_dict.get("servers")
                if servers_list is not None:
                    for j in range(0, len(servers_list)):
                        servers_dict = servers_list[j]
                        vm_list.append(servers_dict.get("uuid"))

            # Count vm_list
            if len(vm_list) == 0:
                self.rc_util.syslogout_ex("RecoveryControllerStarter_0014",
                                          syslog.LOG_INFO)
                msg = "There is no instance in " + notification_hostname + "."
                self.rc_util.syslogout(msg, syslog.LOG_INFO)

                # update record in notification_list
                self.rc_util_db.update_notification_list_db(
                    'progress', 2, notification_id)

                return
            else:
                conf_db_dic = self.rc_config.get_value('db')

                # Connect db
                db = MySQLdb.connect(host=conf_db_dic.get("host"),
                                     db=conf_db_dic.get("name"),
                                     user=conf_db_dic.get("user"),
                                     passwd=conf_db_dic.get("passwd"),
                                     charset=conf_db_dic.get("charset"))

                # Update reserve_list db
                cursor = db.cursor(MySQLdb.cursors.DictCursor)

                sql = ("select recover_to "
                       "from notification_list "
                       "where notification_id='%s' "
                       "for update") % (notification_id)

                cnt = cursor.execute(sql)

                result = cursor.fetchone()
                recover_to = result.get('recover_to')

                if retry_mode is False:
                    sql = ("select * from reserve_list "
                           "where deleted=0 and hostname='%s' "
                          ) % (recover_to)
                    cnt = cursor.execute(sql)

                    if cnt == 0:
                        sql = ("select hostname from reserve_list "
                               "where deleted=0 and cluster_port='%s' "
                               "and hostname!='%s' "
                               "order by create_at asc limit 1 for update"
                              ) % (notification_cluster_port,
                                   notification_hostname)
                        cnt = cursor.execute(sql)

                        if cnt == 0:
                            self.rc_util.syslogout_ex(
                                "RecoveryControllerStarter_0022",
                                syslog.LOG_WARNING)
                            msg = "The reserve node not exist in " \
                                  "reserve_list DB, " \
                                  "so do not recover instances."
                            self.rc_util.syslogout(msg, syslog.LOG_WARNING)

                            cursor.close()
                            db.close()

                            self.rc_util_db.update_notification_list_db(
                                'progress', 3, notification_id)
                            return

                        result = cursor.fetchone()
                        recover_to = result.get('hostname')
                        update_at = datetime.datetime.now()
                        sql = ("update notification_list "
                               "set update_at='%s', recover_to='%s' "
                               "where notification_id='%s'"
                              ) % (update_at, recover_to, notification_id)
                        cursor.execute(sql)

                        self.rc_util.syslogout_ex(
                            "RecoveryControllerStarter_0024", syslog.LOG_INFO)
                        self.rc_util.syslogout("SQL=" + sql, syslog.LOG_INFO)

                self.rc_util.syslogout_ex("RecoveryControllerStarter_0015",
                                          syslog.LOG_INFO)

                delete_at = datetime.datetime.now()

                sql = "update reserve_list set deleted=1 , " \
                      "delete_at='%s' " \
                      "where hostname='%s' " \
                      % (delete_at, recover_to)

                self.rc_util.syslogout(sql, syslog.LOG_INFO)
                cursor.execute(sql)

                db.commit()

                cursor.close()
                db.close()

            # create semaphore (Multiplicity is get from config.)
            conf_dict = self.rc_config.get_value('recover_starter')
            sem_recovery_instance = threading.Semaphore(
                int(conf_dict.get('semaphore_multiplicity')))

            incomplete_list = []
            for i in range(0, int(recovery_max_retry_cnt)):
                incomplete_list = []

                for vm_uuid in vm_list:
                    ret = self._create_vm_list_db_for_failed_host(
                        notification_id, vm_uuid)

                    if ret == 0:
                        threading.Thread(
                            target=self.rc_worker.recovery_instance,
                            args=(vm_uuid, sem_recovery_instance)).start()
                    else:
                        incomplete_list.append(vm_uuid)

                if incomplete_list:
                    vm_list = incomplete_list
                    greenthread.sleep(int(recovery_retry_interval))
                else:
                    break

            for vm_uuid in incomplete_list:
                self.rc_util_db.insert_vm_list_db(
                    notification_id, vm_uuid, 0)

                threading.Thread(
                    target=self.rc_worker.recovery_instance,
                    args=(vm_uuid, sem_recovery_instance)).start()

            # update record in notification_list
            self.rc_util_db.update_notification_list_db(
                'progress', 2, notification_id)

            return

        except MySQLdb.Error:
            self.rc_util.syslogout_ex("RecoveryControllerStarter_0016",
                                      syslog.LOG_ERR)
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            return
        except KeyError:
            self.rc_util.syslogout_ex("RecoveryControllerStarter_0017",
                                      syslog.LOG_ERR)
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            return
        except:
            self.rc_util.syslogout_ex("RecoveryControllerStarter_0018",
                                      syslog.LOG_ERR)
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            return

    def handle_pending_instances(self):
        try:
            # [db]section
            db_dic = self.rc_config.get_value("db")
            db_host = db_dic.get("host")
            db_name = db_dic.get("name")
            db_user = db_dic.get("user")
            db_passwd = db_dic.get("passwd")
            db_charset = db_dic.get("charset")

            # [recover_starter]section
            recover_starter_dic = self.rc_config.get_value("recover_starter")
            semaphore_multiplicity = recover_starter_dic.get(
                "semaphore_multiplicity")

            # Select vm_list
            # Connect db
            connector = MySQLdb.connect(host=db_host,
                                        db=db_name,
                                        user=db_user,
                                        passwd=db_passwd,
                                        charset=db_charset
                                        )

            # get the list of instances pending recovery events
            cursor = connector.cursor(MySQLdb.cursors.DictCursor)
            instance_count = cursor.execute(
                "SELECT uuid FROM vm_list "
                "WHERE progress = 0 or progress = 1")

            result = cursor.fetchall()

            # Connection close
            cursor.close()
            connector.close()

            # Set multiplicity by semaphore_multiplicity
            sem = threading.Semaphore(int(semaphore_multiplicity))

            # Execute vm_recovery_worker
            if instance_count > 0:

                # Execute the required number
                for row in result:
                    threading.Thread(
                        target=self.rc_worker.recovery_instance,
                        args=(row.get("uuid"), sem)).start()

            # Imperfect_recover
            else:
                return

            return
        except MySQLdb.Error:
            self.rc_util.syslogout_ex("RecoveryControllerStarter_0019",
                                      syslog.LOG_ERR)
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            return
        except KeyError:
            self.rc_util.syslogout_ex("RecoveryControllerStarter_0020",
                                      syslog.LOG_ERR)
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            return
        except:
            self.rc_util.syslogout_ex("RecoveryControllerStarter_0021",
                                      syslog.LOG_ERR)
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            return

