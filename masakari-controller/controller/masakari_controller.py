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
This file defines the RecoveryController class.
"""

import eventlet
from eventlet import wsgi
import syslog
import json
from sqlalchemy import exc
import sys
import ConfigParser
import threading
import traceback
import datetime
import socket
import os
import traceback
import logging
from eventlet import greenthread

parentdir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                         os.path.pardir))
# rootdir = os.path.abspath(os.path.join(parentdir, os.path.pardir))
# project root directory needs to be add at list head rather than tail
# this file named 'masakari' conflicts to the directory name
sys.path = [parentdir] + sys.path

import controller.masakari_starter as starter
from controller.masakari_util import RecoveryControllerUtil as util
from controller.masakari_util import RecoveryControllerUtilDb as util_db
import controller.masakari_config as config
import controller.masakari_worker as worker
import db.api as dbapi


class RecoveryController(object):

    """
    RecoveryController class:
    This class starts the wsgi server,
    and waits for notification of the failure detection process on the
    ComputeNode.
    If this class received notification,
    it starts thread that executes the VM recovery process according to the
    contents of the notification.
    """

    def __init__(self):
        """
        Constructor:
        This constructor creates
        RecoveryController object,
        RecoveryControllerStarter object,
        RecoveryControllerUtil object,
        RecoveryControllerWorker object.
        """
        try:
            self.rc_config = config.RecoveryControllerConfig()
            self.rc_starter = starter.RecoveryControllerStarter(
                self.rc_config)
            self.rc_util = util(self.rc_config)
            self.rc_util_db = util_db(self.rc_config)
            self.rc_worker = worker.RecoveryControllerWorker(self.rc_config)
        except:
            logger = logging.getLogger()
            logger.setLevel(logging.ERROR)
            f = "%(asctime)s " + \
                " masakari(%(process)d): %(levelname)s: %(message)s'"
            formatter = logging.Formatter(fmt=f, datefmt='%b %d %H:%M:%S')
            fh = logging.FileHandler(
                filename='/var/log/masakari/masakari-controller.log')
            fh.setLevel(logging.ERROR)
            fh.setFormatter(formatter)
            logger.addHandler(fh)

            msg = "--MonitoringMessage--ID:[%s]" % ("RecoveryController_0003")
            logger.error(msg)

            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            logger.error(error_type)
            logger.error(error_value)

            for tb in tb_list:
                logger.error(tb)

            logger.removeHandler(fh)

            sys.exit()

    def masakari(self):
        """
        RecoveryController class main processing:
        This processing checks the VM list table of DB.
        If an unprocessed VM exists, and start thread to execute the recovery
        process.
        Then, the processing starts the wsgi server and waits for the
        notification.
        """

        try:
            self.rc_util.syslogout_ex(
                "RecoveryController_0004", syslog.LOG_INFO)
            self.rc_util.syslogout(
                "masakari START.", syslog.LOG_INFO)

            # conn = None
            # cursor = None
            # # Get database session
            # conn, cursor = self.rc_util_db.connect_database()

            # Get a session and do not pass it to other threads
            db_engine = dbapi.get_engine()
            session = dbapi.get_session(db_engine)

            self._update_old_records_notification_list(session)
            result = self._find_reprocessing_records_notification_list(session)
            # self.rc_util_db.disconnect_database(conn, cursor)
            preprocessing_count = len(result)

            if preprocessing_count > 0:
                for row in result:
                    if row.recover_by == 0:
                        # node recovery event
                        th = threading.Thread(
                            target=self.rc_worker.host_maintenance_mode,
                            args=(row.notification_id,
                                  row.notification_hostname,
                                  False,))
                        th.start()

                        # Sleep until updating nova-compute service status
                        # down.
                        self.rc_util.syslogout_ex(
                            "RecoveryController_0035", syslog.LOG_INFO)
                        dic = self.rc_config.get_value('recover_starter')
                        node_err_wait = dic.get("node_err_wait")
                        msg = "Sleeping %s sec before starting node recovery thread, until updateing nova-compute service status." % (
                            node_err_wait)
                        self.rc_util.syslogout(msg, syslog.LOG_INFO)
                        greenthread.sleep(int(node_err_wait))

                        # Start add_failed_host thread
                        # TODO(sampath):
                        # Avoid create thread here,
                        # insted call rc_starter.add_failed_host
                        retry_mode = True
                        th = threading.Thread(
                            target=self.rc_starter.add_failed_host,
                            args=(row.notification_id,
                                  row.notification_hostname,
                                  row.notification_cluster_port,
                                  retry_mode, ))
                        th.start()

                    elif row.recover_by == 1:
                        # instance recovery event
                        # TODO(sampath):
                        # Avoid create thread here,
                        # insted call rc_starter.add_failed_instance
                        th = threading.Thread(
                            target=self.rc_starter.add_failed_instance,
                            args=(row.notification_id,
                                  row.notification_uuid, ))
                        th.start()

                    else:
                        # maintenance mode event
                        th = threading.Thread(
                            target=self.rc_worker.host_maintenance_mode,
                            args=(row.notification_id,
                                  row.notification_hostname,
                                  True, ))
                        th.start()

            # Start handle_pending_instances thread
            # TODO(sampath):
            # Avoid create thread here,
            # insted call rc_starter.handle_pending_instances()
            th = threading.Thread(
                target=self.rc_starter.handle_pending_instances)
            th.start()

            # Start reciever process for notification
            conf_wsgi_dic = self.rc_config.get_value('wsgi')
            wsgi.server(
                eventlet.listen(('', int(conf_wsgi_dic['server_port']))),
                self._notification_reciever)
        except exc.SQLAlchemyError:
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout_ex(
                "RecoveryController_0005", syslog.LOG_ERR)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            sys.exit()
        except KeyError:
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout_ex(
                "RecoveryController_0006", syslog.LOG_ERR)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            sys.exit()
        except:
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout_ex(
                "RecoveryController_0007", syslog.LOG_ERR)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            sys.exit()

    def _update_old_records_notification_list(self, session):
        # Get notification_expiration_sec from config
        conf_dict = self.rc_config.get_value('recover_starter')
        notification_expiration_sec = int(conf_dict.get(
            'notification_expiration_sec'))

        now = datetime.datetime.now()
        # Get border time
        border_time = now - \
            datetime.timedelta(seconds=notification_expiration_sec)
        # border_time_str = border_time.strftime('%Y-%m-%d %H:%M:%S')

        # Set old record progress = 4
        # sql = "SELECT id FROM notification_list " \
        #       "WHERE progress = 0 AND create_at < '%s'" \
        #       % (border_time_str)
        self.rc_util.syslogout_ex("RecoveryControllerl_0047", syslog.LOG_INFO)
        # self.rc_util.syslogout("SQL=" + sql, syslog.LOG_INFO)
        # # cnt = cursor.execute(sql)
        # # result = cursor.fetchall()
        result = dbapi.get_old_records_notification(session, border_time)

        for row in result:
            # sql = "UPDATE notification_list " \
            #       "SET progress = %d, update_at = '%s', delete_at = '%s' " \
            #       "WHERE id = '%s'" \
            #       % (4, datetime.datetime.now(),
            #          datetime.datetime.now(), row.get("id"))
            # self.rc_util.syslogout_ex(
            #     "RecoveryControllerl_0048", syslog.LOG_INFO)
            # self.rc_util.syslogout("SQL=" + sql, syslog.LOG_INFO)
            # cursor.execute(sql)
            # conn.commit()
            dbapi.delet_expired_notification(
                session, 4,
                datetime.datetime.now(),
                datetime.datetime.now(),
                row.id)

    def _find_reprocessing_records_notification_list(self, session):
        return_value = []

        # Get list of notification_uuid
        # sql = "SELECT DISTINCT notification_uuid FROM notification_list " \
        #     "WHERE progress = 0 AND recover_by = 1"
        # self.rc_util.syslogout_ex("RecoveryControllerl_0049", syslog.LOG_INFO)
        # self.rc_util.syslogout("SQL=" + sql, syslog.LOG_INFO)
        # cnt = cursor.execute(sql)
        # result = cursor.fetchall()
        result = dbapi.get_reprocessing_records_list_distinct(session)

        # Get reprocessing record
        for row in result:
            # sql = "SELECT id, notification_id, notification_hostname, " \
            #     "notification_uuid, notification_cluster_port, recover_by " \
            #     "FROM notification_list " \
            #       "WHERE progress = 0 AND notification_uuid = '%s' " \
            #       "ORDER BY create_at DESC, id DESC" \
            #       % (row.get("notification_uuid"))
            self.rc_util.syslogout_ex(
                "RecoveryControllerl_0050", syslog.LOG_INFO)
            # self.rc_util.syslogout("SQL=" + sql, syslog.LOG_INFO)
            # cursor.execute(sql)
            # result2 = cursor.fetchall()
            result2 = dbapi.get_reprocessing_records_list(
                session, row.notification_uuid)
            # First row is reprocessing record.
            row_cnt = 0
            for row2 in result2:
                if row_cnt == 0:
                    return_value.append(row2)
                else:
                    # Update progress
                    # sql = "UPDATE notification_list " \
                    #     "SET progress = %d , update_at = '%s', " \
                    #     "delete_at = '%s' " \
                    #       "WHERE id = '%s'" \
                    #     % (4, datetime.datetime.now(),
                    #        datetime.datetime.now(), row2.get("id"))
                    ct = datetime.datetime.now()
                    dbapi.update_reprocessing_records(
                        session, 4, ct, ct, row2.id)
                    self.rc_util.syslogout_ex(
                        "RecoveryControllerl_0051", syslog.LOG_INFO)
                    # self.rc_util.syslogout("SQL=" + sql, syslog.LOG_INFO)
                    # cursor.execute(sql)
                    # conn.commit()
                row_cnt += 1

        # sql = "SELECT DISTINCT notification_hostname FROM notification_list " \
        #     + "WHERE progress = 0 AND recover_by = 0"
        self.rc_util.syslogout_ex("RecoveryControllerl_0052", syslog.LOG_INFO)
        # self.rc_util.syslogout("SQL=" + sql, syslog.LOG_INFO)
        # cnt = cursor.execute(sql)
        # result = cursor.fetchall()
        result = dbapi.get_notification_list_distinct_hostname(session)

        # Get reprocessing record
        for row in result:
            # sql = "SELECT id, notification_id, notification_hostname, " \
            #       "notification_uuid, notification_cluster_port, recover_by " \
            #       "FROM notification_list " \
            #       "WHERE progress = 0 AND notification_hostname = '%s' " \
            #       "ORDER BY create_at DESC, id DESC" \
            #       % (row.get("notification_hostname"))
            self.rc_util.syslogout_ex(
                "RecoveryControllerl_0053", syslog.LOG_INFO)
            # self.rc_util.syslogout("SQL=" + sql, syslog.LOG_INFO)
            # cursor.execute(sql)
            result2 = dbapi.get_notification_list_by_hostname(
                session, row.notification_hostname)

            # First row is reprocessing record.
            row_cnt = 0
            for row2 in result2:
                if row_cnt == 0:
                    return_value.append(row2)
                else:
                    # Update progress
                    # sql = "UPDATE notification_list " \
                    #       "SET progress = %d , update_at = '%s', " \
                    #       "delete_at = '%s' " \
                    #       "WHERE id = '%s'" \
                    #     % (4, datetime.datetime.now(),
                    #        datetime.datetime.now(), row2.get("id"))
                    ct = datetime.datetime.now()
                    dbapi.update_reprocessing_records(
                        session, 4, ct, ct, row2.id)
                    self.rc_util.syslogout_ex(
                        "RecoveryControllerl_0054", syslog.LOG_INFO)
                    # self.rc_util.syslogout("SQL=" + sql, syslog.LOG_INFO)
                    # cursor.execute(sql)
                    # conn.commit()
                row_cnt += 1

        return return_value

    def _check_json_param(self, json_data):
        try:
            check_id = json_data["id"]
            check_type = json_data["type"]
            check_regionID = json_data["regionID"]
            check_hostname = json_data["hostname"]
            check_uuid = json_data["uuid"]
            check_time = json_data["time"]
            check_eventID = json_data["eventID"]
            check_eventType = json_data["eventType"]
            check_detail = json_data["detail"]
            if check_type != 'VM':
                check_startTime = json_data["startTime"]
                check_endTime = json_data["endTime"]
            check_tzname = json_data["tzname"]
            check_daylight = json_data["daylight"]
            check_cluster_port = json_data["cluster_port"]
            return 0
        except KeyError:
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout_ex(
                "RecoveryController_0008", syslog.LOG_ERR)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            return 1

    def _notification_reciever(self, env, start_response):
        try:
            len = env['CONTENT_LENGTH']
            if len > 0:
                body = env['wsgi.input'].read(len)
                json_data = json.loads(body)

                self.rc_util.syslogout_ex(
                    "RecoveryController_0009", syslog.LOG_INFO)
                msg = "Recieved notification : " + body
                self.rc_util.syslogout(msg, syslog.LOG_INFO)

                ret = self._check_json_param(json_data)
                if ret == 1:
                    # Return Response
                    start_response(
                        '400 Bad Request', [('Content-Type', 'text/plain')])
                    return ['method _notification_reciever returned.\r\n']

                # Insert notification into notification_list_db
                notification_list_dic = {}
                notification_list_dic = self._create_notification_list_db(
                    json_data)

                # Return Response
                start_response('200 OK', [('Content-Type', 'text/plain')])

                if notification_list_dic != {}:
                    # Start thread
                    if notification_list_dic.get("recover_by") == 0 and \
                       notification_list_dic.get("progress") == 0:

                        th = threading.Thread(
                            target=self.rc_worker.host_maintenance_mode,
                            args=(notification_list_dic.get(
                                "notification_id"), notification_list_dic.get(
                                "notification_hostname"),
                                False, ))
                        th.start()

                        # Sleep until nova recognizes the node down.
                        self.rc_util.syslogout_ex(
                            "RecoveryController_0029", syslog.LOG_INFO)
                        dic = self.rc_config.get_value('recover_starter')
                        node_err_wait = dic.get("node_err_wait")
                        msg = "Sleeping %s sec before starting recovery thread until nova recognizes the node down..." % (
                            node_err_wait)
                        self.rc_util.syslogout(msg, syslog.LOG_INFO)
                        greenthread.sleep(int(node_err_wait))

                        retry_mode = False
                        th = threading.Thread(
                            target=self.rc_starter.add_failed_host,
                            args=(notification_list_dic.get(
                                "notification_id"),
                                notification_list_dic.get(
                                "notification_hostname"),
                                notification_list_dic.get(
                                "notification_cluster_port"),
                                retry_mode, ))

                        th.start()
                    elif notification_list_dic.get("recover_by") == 0 and \
                            notification_list_dic.get("progress") == 3:
                        th = threading.Thread(
                            target=self.rc_worker.host_maintenance_mode,
                            args=(notification_list_dic.get(
                                "notification_id"),
                                notification_list_dic.get(
                                "notification_hostname"),
                                False, ))
                        th.start()
                    elif notification_list_dic.get("recover_by") == 1:
                        retry_mode = False
                        th = threading.Thread(
                            target=self.rc_starter.add_failed_instance,
                            args=(
                                notification_list_dic.get("notification_id"),
                                notification_list_dic.get(
                                    "notification_uuid"), retry_mode, )
                        )
                        th.start()
                    elif notification_list_dic.get("recover_by") == 2:
                        th = threading.Thread(
                            target=self.rc_worker.host_maintenance_mode,
                            args=(
                                notification_list_dic.get("notification_id"),
                                notification_list_dic.get(
                                    "notification_hostname"),
                                True, )
                        )
                        th.start()
                    else:
                        self.rc_util.syslogout_ex(
                            "RecoveryController_0010", syslog.LOG_INFO)
                        self.rc_util.syslogout(
                            "Column \"recover_by\" \
                            on notification_list DB is invalid value.",
                            syslog.LOG_INFO)

        except exc.SQLAlchemyError:
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout_ex(
                "RecoveryController_0011", syslog.LOG_ERR)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            start_response(
                '500 Internal Server Error', [('Content-Type', 'text/plain')])
        except KeyError:
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout_ex(
                "RecoveryController_0012", syslog.LOG_ERR)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            start_response(
                '500 Internal Server Error', [('Content-Type', 'text/plain')])
        except:
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout_ex(
                "RecoveryController_0013", syslog.LOG_ERR)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            start_response(
                '500 Internal Server Error', [('Content-Type', 'text/plain')])

        return ['method _notification_reciever returned.\r\n']

    def _create_notification_list_db(self, jsonData):
        ret_dic = {}

        # Get DB from here and pass it to _check_retry_notification
        try:
            # Get session for db
            db_engine = dbapi.get_engine()
            session = dbapi.get_session(db_engine)
            # conn=None
            # cursor=None
            # Get database connection
            # conn, cursor=self.rc_util_db.connect_database()
            # Lock notification_list table

            # table_name='notification_list'
            # self.rc_util_db.run_lock_query(table_name, cursor)

            if self._check_retry_notification(jsonData, session):
                self.rc_util.syslogout_ex(
                    "RecoveryController_0030", syslog.LOG_INFO)
                msg = "Duplicate notifications. id:" + jsonData.get("id")
                self.rc_util.syslogout(msg, syslog.LOG_INFO)
                self.rc_util.syslogout(jsonData, syslog.LOG_INFO)

            # Node Recovery(processing A)
            elif jsonData.get("type") == "rscGroup" and \
                    str(jsonData.get("eventID")) == "1" and \
                    str(jsonData.get("eventType")) == "2" and \
                    str(jsonData.get("detail")) == "2":

                tdatetime = datetime.datetime.strptime(
                    jsonData.get("time"), '%Y%m%d%H%M%S')
                if not self._check_repeated_notify(tdatetime,
                                                   jsonData.get("hostname"),
                                                   session):
                    recover_by = 0  # node recovery
                    ret_dic = self.rc_util_db.insert_notification_list_db(
                        jsonData, recover_by, session)
                    self.rc_util.syslogout_ex(
                        "RecoveryController_0014", syslog.LOG_INFO)
                    self.rc_util.syslogout(jsonData, syslog.LOG_INFO)
                else:
                    # Duplicate notifications.
                    self.rc_util.syslogout_ex(
                        "RecoveryController_0015", syslog.LOG_INFO)
                    msg = "Duplicate notifications. id:" + jsonData.get("id")
                    self.rc_util.syslogout(msg, syslog.LOG_INFO)
                    self.rc_util.syslogout(jsonData, syslog.LOG_INFO)

            # VM Recovery(processing G)
            elif jsonData.get("type") == 'VM' and \
                    str(jsonData.get("eventID")) == '0' and \
                    str(jsonData.get("eventType")) == '5' and \
                    str(jsonData.get("detail")) == '5':

                recover_by = 1  # VM recovery
                ret_dic = self.rc_util_db.insert_notification_list_db(
                    jsonData, recover_by, session)
                self.rc_util.syslogout_ex(
                    "RecoveryController_0019", syslog.LOG_INFO)
                self.rc_util.syslogout(jsonData, syslog.LOG_INFO)

            # Node Lock(processing D and F)
            # Node will be locked.
            elif (jsonData.get("type") == 'nodeStatus') or \
                 ((jsonData.get("type") == 'rscGroup' and
                   str(jsonData.get("eventID")) == '1' and
                   str(jsonData.get("eventType")) == '2') and
                  (str(jsonData.get("detail")) == '3' or
                   str(jsonData.get("detail")) == '4')):

                tdatetime = datetime.datetime.strptime(
                    jsonData.get("time"), '%Y%m%d%H%M%S')
                if not self._check_repeated_notify(tdatetime,
                                                   jsonData.get("hostname"),
                                                   session):

                    recover_by = 2  # NODE lock
                    ret_dic = self.rc_util_db.insert_notification_list_db(
                        jsonData, recover_by, session)
                    self.rc_util.syslogout_ex(
                        "RecoveryController_0021", syslog.LOG_INFO)
                    self.rc_util.syslogout(jsonData, syslog.LOG_INFO)
                else:
                    # Duplicate notifications.
                    self.rc_util.syslogout_ex(
                        "RecoveryController_0036", syslog.LOG_INFO)
                    msg = "Duplicate notifications. id:" + jsonData.get("id")
                    self.rc_util.syslogout(msg, syslog.LOG_INFO)
                    self.rc_util.syslogout(jsonData, syslog.LOG_INFO)

            # Do not recover(Excuted Stop API)
            elif jsonData.get("type") == "VM" and \
                    str(jsonData.get("eventID")) == "0" and \
                    str(jsonData.get("eventType")) == "5" and \
                    str(jsonData.get("detail")) == "1":
                self.rc_util.syslogout_ex(
                    "RecoveryController_0022", syslog.LOG_INFO)
                self.rc_util.syslogout(jsonData, syslog.LOG_INFO)
                msg = "Do not recover instance.(Excuted Stop API)"
                self.rc_util.syslogout(msg, syslog.LOG_INFO)

            # Notification of starting node.
            elif jsonData.get("type") == "rscGroup" and \
                    str(jsonData.get("eventID")) == "1" and \
                    str(jsonData.get("eventType")) == "1" and \
                    str(jsonData.get("detail")) == "1":
                self.rc_util.syslogout_ex(
                    "RecoveryController_0023", syslog.LOG_INFO)
                self.rc_util.syslogout(jsonData, syslog.LOG_INFO)
                msg = "Recieved notification of node starting. Node:" + \
                      jsonData['hostname']
                self.rc_util.syslogout(msg, syslog.LOG_INFO)

            # Ignore notification
            else:
                self.rc_util.syslogout_ex(
                    "RecoveryController_0024", syslog.LOG_INFO)
                self.rc_util.syslogout(jsonData, syslog.LOG_INFO)
                msg = "Ignore notification. Notification:" + str(jsonData)
                self.rc_util.syslogout(msg, syslog.LOG_INFO)
        except Exception:
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            self.rc_util.syslogout_ex(
                "RecoveryController_0046", syslog.LOG_ERR)
            self.rc_util.syslogout(error_type, syslog.LOG_ERR)
            self.rc_util.syslogout(error_value, syslog.LOG_ERR)
            for tb in tb_list:
                self.rc_util.syslogout(tb, syslog.LOG_ERR)
            raise
        return ret_dic

    def _check_retry_notification(self, jsonData, session):

        notification_id = jsonData.get("id")
        # # Execute SQL
        # sql = "SELECT notification_id FROM notification_list " \
        #       "WHERE notification_id = '%s'" % (notification_id)
        # cnt = cursor.execute(sql)

        cnt = dbapi.get_all_notification_list_by_notification_id(
            sessaion, notification_id)
        # if cnt is 0, not duplicate notification.
        if not cnt:
            return 0
        else:
            return 1

    def _check_repeated_notify(self, notification_time,
                               notification_hostname, session):
        # sql = "SELECT notification_time FROM notification_list " \
        #     "WHERE notification_hostname = '%s'" \
        #     "AND notification_type = 'rscGroup'" \
        #     % (notification_hostname)
        # cnt = cursor.execute(sql)
        result = dbapi.get_all_notification_list_by_hostname_with_rscgroup_type(
            session, notification_hostname)
        # if cnt is 0, not duplicate notification.
        if not result:
            return 0

        # result = cursor.fetchall()

        conf_recover_starter_dic = self.rc_config.get_value('recover_starter')
        notification_time_difference = conf_recover_starter_dic.get(
            "notification_time_difference")

        # Compare timestamp in db and timestamp in notification
        flg = 0
        for row in result:
            db_time = row.notification_time
            delta = notification_time - db_time
            if long(delta.total_seconds()) <= long(
                    notification_time_difference):
                flg = 1

        return flg


if __name__ == '__main__':
    rc = RecoveryController()
    rc.masakari()
