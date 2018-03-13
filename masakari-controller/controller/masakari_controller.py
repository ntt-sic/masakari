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
import json
import sys
import ConfigParser
import threading
import traceback
import datetime
import socket
import os
import errno
import traceback
import logging
import calendar
from eventlet import wsgi
from eventlet import greenthread
from sqlalchemy import exc

parentdir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                         os.path.pardir))
# rootdir = os.path.abspath(os.path.join(parentdir, os.path.pardir))
# project root directory needs to be add at list head rather than tail
# this file named 'masakari' conflicts to the directory name
if parentdir not in sys.path:
    sys.path = [parentdir] + sys.path

import controller.masakari_starter as starter
from controller.masakari_util import RecoveryControllerUtil as util
from controller.masakari_util import RecoveryControllerUtilDb as util_db
from controller.masakari_util import RecoveryControllerUtilApi as util_api
from controller.masakari_util import LogProcessBeginAndEnd
from oslo_log import log as oslo_logging
import controller.masakari_config as config
import controller.masakari_worker as worker
import db.api as dbapi

LOG = oslo_logging.getLogger('controller.masakari_controller')
log_process_begin_and_end = LogProcessBeginAndEnd(LOG)
NOTIFICATION_LIST = "notification_list"


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
        RecoveryControllerWorker object.
        """
        try:
            self.rc_config = config.RecoveryControllerConfig()
            self.rc_util = util()

            msg = "Succeeded in reading the configration file."
            LOG.info(msg)

            self.rc_starter = starter.RecoveryControllerStarter(
                self.rc_config)
            self.rc_util_db = util_db(self.rc_config)
            self.rc_util_api = util_api(self.rc_config)
            self.rc_worker = worker.RecoveryControllerWorker(self.rc_config)

        except Exception as e:
            logger = logging.getLogger()
            logger.setLevel(logging.ERROR)
            f = "%(asctime)s " + \
                " masakari(%(process)d): %(levelname)s: %(message)s'"
            formatter = logging.Formatter(fmt=f, datefmt='%b %d %H:%M:%S')

            # create log dir if not created
            log_dir = '/var/log/masakari/'
            try:
                os.makedirs(log_dir)
            except OSError as exc:
                if exc.errno == errno.EEXIST and os.path.isdir(log_dir):
                    pass
                else:
                    raise

            fh = logging.FileHandler(
                filename='/var/log/masakari/masakari-controller.log')
            fh.setLevel(logging.ERROR)
            fh.setFormatter(formatter)
            logger.addHandler(fh)

            msg = ("An error during initializing masakari controller: %s" % e)
            logger.critical(msg)

            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            logger.error(error_type)
            logger.error(error_value)

            for tb in tb_list:
                logger.error(tb)

            logger.removeHandler(fh)

            sys.exit()

    @log_process_begin_and_end.output_log
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
            LOG.info("masakari START.")

            # Get a session and do not pass it to other threads
            db_engine = dbapi.get_engine(self.rc_config)
            session = dbapi.get_session(db_engine)

            self._update_old_records_notification_list(session)
            result = self._find_reprocessing_records_notification_list(session)
            preprocessing_count = len(result)

            if preprocessing_count > 0:
                for row in result:
                    if row.recover_by == 0:
                        # node recovery event
                        msg = "Run thread rc_worker.host_maintenance_mode." \
                            + " notification_id=" + row.notification_id \
                            + " notification_hostname=" \
                            + row.notification_hostname \
                            + " update_progress=False"
                        LOG.info(msg)
                        thread_name = self.rc_util.make_thread_name(
                            NOTIFICATION_LIST,
                            row.notification_id)
                        th = threading.Thread(
                            target=self.rc_worker.host_maintenance_mode,
                            name=thread_name,
                            args=(row.notification_id,
                                  row.notification_hostname,
                                  False,))
                        th.start()

                        # Sleep until updating nova-compute service status
                        # down.
                        dic = self.rc_config.get_value('recover_starter')
                        node_err_wait = dic.get("node_err_wait")
                        msg = ("Sleeping %s sec before starting node recovery"
                               "thread, until updateing nova-compute"
                               "service status." % (node_err_wait))
                        LOG.info(msg)
                        greenthread.sleep(int(node_err_wait))

                        # Start add_failed_host thread
                        # TODO(sampath):
                        # Avoid create thread here,
                        # insted call rc_starter.add_failed_host
                        retry_mode = True
                        msg = "Run thread rc_starter.add_failed_host." \
                            + " notification_id=" + row.notification_id \
                            + " notification_hostname=" \
                            + row.notification_hostname \
                            + " notification_cluster_port=" \
                            + row.notification_cluster_port \
                            + " retry_mode=" + str(retry_mode)
                        LOG.info(msg)
                        thread_name = self.rc_util.make_thread_name(
                            NOTIFICATION_LIST,
                            row.notification_id)
                        th = threading.Thread(
                            target=self.rc_starter.add_failed_host,
                            name=thread_name,
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
                        msg = "Run thread rc_starter.add_failed_instance." \
                            + " notification_id=" + row.notification_id \
                            + " notification_uuid=" \
                            + row.notification_uuid
                        LOG.info(msg)
                        thread_name = self.rc_util.make_thread_name(
                            NOTIFICATION_LIST,
                            row.notification_id)
                        th = threading.Thread(
                            target=self.rc_starter.add_failed_instance,
                            name=thread_name,
                            args=(row.notification_id,
                                  row.notification_uuid, ))
                        th.start()

                    else:
                        # maintenance mode event
                        msg = "Run thread rc_starter.host_maintenance_mode." \
                            + " notification_id=" + row.notification_id \
                            + " notification_hostname=" \
                            + row.notification_hostname \
                            + "update_progress=True"
                        LOG.info(msg)
                        thread_name = self.rc_util.make_thread_name(
                            NOTIFICATION_LIST,
                            row.notification_id)
                        th = threading.Thread(
                            target=self.rc_worker.host_maintenance_mode,
                            name=thread_name,
                            args=(row.notification_id,
                                  row.notification_hostname,
                                  True, ))
                        th.start()

            # Start handle_pending_instances thread
            # TODO(sampath):
            # Avoid create thread here,
            # insted call rc_starter.handle_pending_instances()
            msg = "Run thread rc_starter.handle_pending_instances."
            LOG.info(msg)
            thread_name = "Thread:handle_pending_instances"
            th = threading.Thread(
                target=self.rc_starter.handle_pending_instances,
                name=thread_name)
            th.start()

            # Start reciever process for notification
            conf_wsgi_dic = self.rc_config.get_value('wsgi')
            wsgi.server(
                eventlet.listen(('', int(conf_wsgi_dic['server_port']))),
                self._notification_reciever)

        except exc.SQLAlchemyError:
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.critical(error_type)
            LOG.critical(error_value)
            for tb in tb_list:
                LOG.critical(tb)

            sys.exit()
        except KeyError:
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.critical(error_type)
            LOG.critical(error_value)
            for tb in tb_list:
                LOG.critical(tb)

            sys.exit()
        except:
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.critical(error_type)
            LOG.critical(error_value)
            for tb in tb_list:
                LOG.critical(tb)

            sys.exit()

    @log_process_begin_and_end.output_log
    def _update_old_records_notification_list(self, session):
        # Get notification_expiration_sec from config

        conf_dict = self.rc_config.get_value('recover_starter')
        notification_expiration_sec = int(conf_dict.get(
            'notification_expiration_sec'))

        now = datetime.datetime.now()
        # Get border time
        border_time = now - datetime.timedelta(
            seconds=notification_expiration_sec)

        msg = "Do get_old_records_notification."
        LOG.info(msg)
        result = dbapi.get_old_records_notification(session, border_time)
        msg = "Succeeded in get_old_records_notification. " \
            + "Return_value = " + str(result)
        LOG.info(msg)

        for row in result:
            msg = "Do delete_expired_notification."
            LOG.info(msg)
            dbapi.delete_expired_notification(
                session,
                datetime.datetime.now(),
                datetime.datetime.now(),
                row.id)
            msg = "Succeeded in delete_expired_notification."
            LOG.info(msg)

    @log_process_begin_and_end.output_log
    def _find_reprocessing_records_notification_list(self, session):

        return_value = []
        msg = "Do get_reprocessing_records_list_distinct."
        LOG.info(msg)
        result = dbapi.get_reprocessing_records_list_distinct(session)
        msg = "Succeeded in get_reprocessing_records_list_distinct. " \
            + "Return_value = " + str(result)
        LOG.info(msg)

        # Get reprocessing record
        for row in result:
            msg = "Do get_reprocessing_records_list."
            LOG.info(msg)
            result2 = dbapi.get_reprocessing_records_list(
                session, row.notification_uuid)
            msg = "Succeeded in get_reprocessing_records_list. " \
                + "Return_value = " + str(result2)
            LOG.info(msg)
            # First row is reprocessing record.
            row_cnt = 0
            for row2 in result2:
                if row_cnt == 0:
                    return_value.append(row2)
                else:
                    ct = datetime.datetime.now()
                    msg = "Do update_reprocessing_records."
                    LOG.info(msg)
                    dbapi.update_reprocessing_records(
                        session, 4, ct, ct, row2.id)
                    msg = "Succeeded in update_reprocessing_records."
                    LOG.info(msg)
                row_cnt += 1
        msg = "Do get_notification_list_distinct_hostname."
        LOG.info(msg)
        result = dbapi.get_notification_list_distinct_hostname(session)
        msg = "Succeeded in get_notification_list_distinct_hostname. " \
            + "Return_value = " + str(result)
        LOG.info(msg)

        # Get reprocessing record
        for row in result:
            msg = "Do get_notification_list_by_hostname."
            LOG.info(msg)
            result2 = dbapi.get_notification_list_by_hostname(
                session, row.notification_hostname)
            msg = "Succeeded in get_notification_list_by_hostname. " \
                + "Return_value = " + str(result2)
            LOG.info(msg)
            # First row is reprocessing record.
            row_cnt = 0
            for row2 in result2:
                if row_cnt == 0:
                    return_value.append(row2)
                else:
                    ct = datetime.datetime.now()
                    msg = "Do update_reprocessing_records."
                    LOG.info(msg)
                    dbapi.update_reprocessing_records(
                        session, 4, ct, ct, row2.id)
                    msg = "Succeeded in update_reprocessing_records."
                    LOG.info(msg)
                row_cnt += 1

        return return_value

    @log_process_begin_and_end.output_log
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
            LOG.error(error_type)
            LOG.error(error_value)
            for tb in tb_list:
                LOG.error(tb)

            return 1

    @log_process_begin_and_end.output_log
    def _notification_reciever(self, env, start_response):

        try:
            len = env['CONTENT_LENGTH']
            if len > 0:
                body = env['wsgi.input'].read(len)
                json_data = json.loads(body)

                msg = "Recieved notification : " + body
                LOG.info(msg)

                ret = self._check_json_param(json_data)
                if ret == 1:
                    # Return Response
                    start_response(
                        '400 Bad Request', [('Content-Type', 'text/plain')])

                    msg = "Wsgi response: " \
                          "status=400 Bad Request, " \
                          "body=method _notification_reciever returned."
                    LOG.info(msg)

                    return ['method _notification_reciever returned.\r\n']

                # Insert notification into notification_list_db
                notification_list_dic = {}
                notification_list_dic = self._create_notification_list_db(
                    json_data)

                # Return Response
                start_response('200 OK', [('Content-Type', 'text/plain')])

                msg = "Wsgi response: " \
                    + "status=200 OK, " \
                    + "body=method _notification_reciever returned."
                LOG.info(msg)

                if notification_list_dic != {}:
                    # Start thread
                    if notification_list_dic.get("recover_by") == 0 and \
                       notification_list_dic.get("progress") == 0:

                        msg = "Run thread rc_worker.host_maintenance_mode." \
                            + " notification_id=" \
                            + notification_list_dic.get("notification_id") \
                            + " notification_hostname=" \
                            + notification_list_dic.get(
                                "notification_hostname") \
                            + "update_progress=False"
                        LOG.info(msg)
                        thread_name = self.rc_util.make_thread_name(
                            NOTIFICATION_LIST,
                            notification_list_dic.get("notification_id"))
                        th = threading.Thread(
                            target=self.rc_worker.host_maintenance_mode,
                            name=thread_name,
                            args=(notification_list_dic.get(
                                "notification_id"), notification_list_dic.get(
                                "notification_hostname"),
                                False, ))
                        th.start()

                        dic = self.rc_config.get_value('recover_starter')
                        node_err_wait = dic.get("node_err_wait")
                        msg = ("Before starting recovery thread"
                               "check repeatedly whether nova recognizes"
                               "the node is down (max %s sec)"
                               % (node_err_wait)
                               )
                        LOG.info(msg)

                        node_err_retry_interval = 10
                        node_err_retry_until = calendar.timegm(datetime.datetime.utcnow().timetuple()) + int(node_err_wait)
                        target_hostname = notification_list_dic.get("notification_hostname")
                        LOG.info('target hostname: {0}'.format(target_hostname))
                        while True:
                            if calendar.timegm(datetime.datetime.utcnow().timetuple()) > node_err_retry_until:
                                break

                            LOG.info('check whether the node is down')
                            is_down = self.rc_util_api.check_compute_node_state(hostname=target_hostname, state='down')
                            if is_down:
                                break
                            else:
                                greenthread.sleep(int(node_err_retry_interval))

                        retry_mode = False
                        msg = "Run thread rc_starter.add_failed_host." \
                            + " notification_id=" \
                            + notification_list_dic.get("notification_id") \
                            + " notification_hostname=" \
                            + notification_list_dic.get(
                                "notification_hostname") \
                            + " notification_cluster_port=" \
                            + notification_list_dic.get(
                                "notification_cluster_port") \
                            + " retry_mode=" + str(retry_mode)
                        LOG.info(msg)
                        thread_name = self.rc_util.make_thread_name(
                            NOTIFICATION_LIST,
                            notification_list_dic.get("notification_id"))
                        th = threading.Thread(
                            target=self.rc_starter.add_failed_host,
                            name=thread_name,
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
                        msg = "Run thread rc_worker.host_maintenance_mode." \
                            + " notification_id=" \
                            + notification_list_dic.get("notification_id") \
                            + " notification_hostname=" \
                            + notification_list_dic.get(
                                "notification_hostname") \
                            + "update_progress=False"
                        LOG.info(msg)
                        thread_name = self.rc_util.make_thread_name(
                            NOTIFICATION_LIST,
                            notification_list_dic.get("notification_id"))
                        th = threading.Thread(
                            target=self.rc_worker.host_maintenance_mode,
                            name=thread_name,
                            args=(notification_list_dic.get(
                                "notification_id"),
                                notification_list_dic.get(
                                "notification_hostname"),
                                False, ))
                        th.start()
                    elif notification_list_dic.get("recover_by") == 1:
                        retry_mode = False
                        msg = "Run thread rc_starter.add_failed_instance." \
                            + " notification_id=" \
                            + notification_list_dic.get("notification_id") \
                            + " notification_uuid=" \
                            + notification_list_dic.get("notification_uuid") \
                            + " retry_mode=" + str(retry_mode)
                        LOG.info(msg)
                        thread_name = self.rc_util.make_thread_name(
                            NOTIFICATION_LIST,
                            notification_list_dic.get("notification_id"))
                        th = threading.Thread(
                            target=self.rc_starter.add_failed_instance,
                            name=thread_name,
                            args=(
                                notification_list_dic.get("notification_id"),
                                notification_list_dic.get(
                                    "notification_uuid"), retry_mode, )
                        )
                        th.start()
                    elif notification_list_dic.get("recover_by") == 2:
                        msg = "Run thread rc_worker.host_maintenance_mode." \
                            + " notification_id=" \
                            + notification_list_dic.get("notification_id") \
                            + " notification_hostname=" \
                            + notification_list_dic.get(
                                "notification_hostname") \
                            + "update_progress=False"
                        LOG.info(msg)
                        thread_name = self.rc_util.make_thread_name(
                            NOTIFICATION_LIST,
                            notification_list_dic.get("notification_id"))
                        th = threading.Thread(
                            target=self.rc_worker.host_maintenance_mode,
                            name=thread_name,
                            args=(
                                notification_list_dic.get("notification_id"),
                                notification_list_dic.get(
                                    "notification_hostname"),
                                True, )
                        )
                        th.start()
                    else:
                        LOG.warning(
                            "Column \"recover_by\" \
                            on notification_list DB is invalid value.")

        except exc.SQLAlchemyError:
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(error_type)
            LOG.error(error_value)
            for tb in tb_list:
                LOG.error(tb)
            start_response(
                '500 Internal Server Error', [('Content-Type', 'text/plain')])

            msg = "Wsgi response: " \
                  "status=500 Internal Server Error, " \
                  "body=method _notification_reciever returned."
            LOG.info(msg)

        except KeyError:
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(error_type)
            LOG.error(error_value)
            for tb in tb_list:
                LOG.error(tb)
            start_response(
                '500 Internal Server Error', [('Content-Type', 'text/plain')])

            msg = "Wsgi response: " \
                  "status=500 Internal Server Error, " \
                  "body=method _notification_reciever returned."
            LOG.info(msg)

        except:
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(error_type)
            LOG.error(error_value)
            for tb in tb_list:
                LOG.error(tb)
            start_response(
                '500 Internal Server Error', [('Content-Type', 'text/plain')])

            msg = "Wsgi response: " \
                  "status=500 Internal Server Error, " \
                  "body=method _notification_reciever returned."
            LOG.info(msg)

        return ['method _notification_reciever returned.\r\n']

    @log_process_begin_and_end.output_log
    def _create_notification_list_db(self, jsonData):

        ret_dic = {}

        # Get DB from here and pass it to _check_retry_notification
        try:
            # Get session for db
            db_engine = dbapi.get_engine(self.rc_config)
            session = dbapi.get_session(db_engine)
            if self._check_retry_notification(jsonData, session):
                msg = "Duplicate notifications. id:" + jsonData.get("id")
                LOG.info(msg)
                LOG.info(jsonData)

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
                    LOG.info(jsonData)
                else:
                    # Duplicate notifications.
                    msg = "Duplicate notifications. id:" + jsonData.get("id")
                    LOG.info(msg)
                    LOG.info(jsonData)

            # VM Recovery(processing G)
            elif jsonData.get("type") == 'VM' and \
                    str(jsonData.get("eventID")) == '0' and \
                    str(jsonData.get("eventType")) == '5' and \
                    str(jsonData.get("detail")) == '5':

                recover_by = 1  # VM recovery
                ret_dic = self.rc_util_db.insert_notification_list_db(
                    jsonData, recover_by, session)
                LOG.info(jsonData)

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
                    LOG.info(jsonData)
                else:
                    # Duplicate notifications.
                    msg = "Duplicate notifications. id:" + jsonData.get("id")
                    LOG.info(msg)
                    LOG.info(jsonData)

            # Do not recover(Excuted Stop API)
            elif jsonData.get("type") == "VM" and \
                    str(jsonData.get("eventID")) == "0" and \
                    str(jsonData.get("eventType")) == "5" and \
                    str(jsonData.get("detail")) == "1":
                LOG.info(jsonData)
                msg = "Do not recover instance.(Excuted Stop API)"
                LOG.info(msg)

            # Notification of starting node.
            elif jsonData.get("type") == "rscGroup" and \
                    str(jsonData.get("eventID")) == "1" and \
                    str(jsonData.get("eventType")) == "1" and \
                    str(jsonData.get("detail")) == "1":
                LOG.info(jsonData)
                msg = "Recieved notification of node starting. Node:" + \
                      jsonData['hostname']
                LOG.info(msg)

            # Ignore notification
            else:
                LOG.info(jsonData)
                msg = "Ignore notification. Notification:" + str(jsonData)
                LOG.info(msg)
        except Exception:
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(error_type)
            LOG.error(error_value)
            for tb in tb_list:
                LOG.error(tb)
            raise

        return ret_dic

    @log_process_begin_and_end.output_log
    def _check_retry_notification(self, jsonData, session):

        notification_id = jsonData.get("id")
        msg = "Do get_all_notification_list_by_notification_id."
        LOG.info(msg)
        cnt = dbapi.get_all_notification_list_by_notification_id(
            session, notification_id)
        msg = "Succeeded in get_all_notification_list_by_notification_id. " \
            + "Return_value = " + str(cnt)
        LOG.info(msg)
        # if cnt is 0, not duplicate notification.
        if not cnt:
            return 0
        else:
            return 1

    @log_process_begin_and_end.output_log
    def _check_repeated_notify(self, notification_time,
                               notification_hostname, session):

        msg = "Do get_all_notification_list_by_hostname_type."
        LOG.info(msg)
        result = dbapi.get_all_notification_list_by_hostname_type(
            session, notification_hostname)
        msg = "Succeeded in get_all_notification_list_by_hostname_type. " \
            + "Return_value = " + str(result)

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


def main():
    rc = RecoveryController()
    rc.masakari()

if __name__ == '__main__':
    main()
