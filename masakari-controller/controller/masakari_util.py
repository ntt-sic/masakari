# !/usr/bin/env python
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
Management module of utility classes for VM recovery control
"""
import ConfigParser
import datetime
import json
import os
import paramiko
import re
import masakari_config as config
import socket
import subprocess
import sys
import threading
import traceback
import errno

from eventlet import greenthread
from keystoneauth1 import loading
from keystoneauth1 import session
from keystoneclient import client as keystone_client
from novaclient import client as nova_client
from novaclient import exceptions
from sqlalchemy import exc

parentdir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                         os.path.pardir))
# rootdir = os.path.abspath(os.path.join(parentdir, os.path.pardir))
# project root directory needs to be add at list head rather than tail
# this file named 'masakari' conflicts to the directory name
if parentdir not in sys.path:
    sys.path = [parentdir] + sys.path

import db.api as dbapi
from db.models import NotificationList, VmList, ReserveList

from oslo_log import log as logging
from functools import wraps

LOG = logging.getLogger(__name__)


class LogProcessBeginAndEnd(object):

    def __init__(self, logger):
        self.LOG = logger

    def output_log(self, func):
        @wraps(func)
        def _output_log(*args, **kwargs):
            start_msg = ("BEGIN %s: parameters are %s, %s") % (
                func.__name__, args, kwargs)
            self.LOG.debug(start_msg)

            ret = func(*args, **kwargs)

            end_msg = ("END %s: return %s") % (func.__name__, ret)
            self.LOG.debug(end_msg)

            return ret
        return _output_log

log_process_begin_and_end = LogProcessBeginAndEnd(LOG)


class RecoveryControllerUtilDb(object):

    """
    DB-related utility classes for VM recovery control
    """

    def __init__(self, config_object):
        self.rc_config = config_object

    @log_process_begin_and_end.output_log
    def insert_vm_list_db(self, session, notification_id,
                          notification_uuid, retry_cnt):
        """
        VM list table registration
        :param :cursor: cursor object
        :param :notification_id: Notification ID
                (used as search criteria for notification list table)
        :param :notification_uuid:VM of uuid
                (used as the registered contents of the VM list table)
        :param :retry_cnt:Retry count
                (used as the registered contents of the VM list table)
        :return :primary_id: The value of LAST_INSERT_ID
        """

        try:
            msg = "Do get_all_notification_list_by_notification_id."
            LOG.info(msg)
            res = dbapi.get_all_notification_list_by_notification_id(
                session,
                notification_id
            )
            msg = "Succeeded in get_all_notification_list_by_notification_id. " \
                + "Return_value = " + str(res)
            LOG.info(msg)
            # Todo(sampath): select first and only object from the list
            # log if many records
            notification_recover_to = res[0].recover_to
            notification_recover_by = res[0].recover_by
            msg = "Do add_vm_list."
            LOG.info(msg)
            vm_item = dbapi.add_vm_list(session,
                                        datetime.datetime.now(),
                                        "0",
                                        notification_uuid,
                                        "0",
                                        str(retry_cnt),
                                        notification_id,
                                        notification_recover_to,
                                        str(notification_recover_by)
                                        )
            msg = "Succeeded in add_vm_list. " \
                + "Return_value = " + str(vm_item)
            LOG.info(msg)

            primary_id = vm_item.id

            return primary_id

        except KeyError:

            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(error_type)
            LOG.error(error_value)
            for tb in tb_list:
                LOG.error(tb)

            msg = "Exception : KeyError in insert_vm_list_db()."
            LOG.error(msg)

            raise KeyError

        except exc.SQLAlchemyError:
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(error_type)
            LOG(error_value)
            for tb in tb_list:
                LOG.error(tb)

            msg = "Exception : sqlalchemy error in insert_vm_list_db()."
            LOG.error(msg)

            raise exc.SQLAlchemyError

        except:
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(error_type)
            LOG.error(error_value)

            for tb in tb_list:
                LOG.error(tb)

            msg = "Exception : Exception in insert_vm_list_db()."
            LOG.error(msg)

            raise

    @log_process_begin_and_end.output_log
    def insert_notification_list_db(self, jsonData, recover_by, session):
        """
           Insert into notification_list DB from notification JSON.
           :param :jsonData: notifocation json data.
           :param :recover_by:node recover(0)/VM recover(1)/process error(2)
           :param :cursor: cursor object
           :return :ret_dic:and return the information that was registered to
                       notification_list table in the dictionary type

        """

        # NOTE: The notification item 'endTime' may have a NULL value.
        #       reference : The Notification Spec for RecoveryController.
        # JSON decoder perform null -> None translation
        try:
            if not jsonData.get("endTime"):
                j_endTime = None
            else:
                j_endTime = datetime.datetime.strptime(
                    jsonData.get("endTime"), '%Y%m%d%H%M%S')
            # update and deleted :not yet
            create_at = datetime.datetime.now()
            update_at = None
            delete_at = None
            deleted = 0
            # progress 0:not yet
            progress = 0
            # From /etc/hosts
            # NOTE: Hosts hostname suffix is
            # undetermined("_data_line","_control_line")
            iscsi_ip = None
            controle_ip = socket.gethostbyname(jsonData.get("hostname"))
            recover_to = None
            if recover_by == 0:
                recover_to = self._get_reserve_node_from_reserve_list_db(
                    jsonData.get("cluster_port"),
                    jsonData.get("hostname"),
                    session)
                # If reserve node is None, set progress 3.
                if recover_to is None:
                    progress = 3

            def strp_time(u_time):
                """
                Convert unicode time with format '%Y%m%d%H%M%S' to
                datetime format.
                """
                try:
                    d = datetime.datetime.strptime(u_time, '%Y%m%d%H%M%S')

                except (ValueError, TypeError) as e:
                    LOG.warning(e)
                    d = None

                return d

            notification_time = strp_time(jsonData.get("time"))
            notification_startTime = strp_time(jsonData.get("startTime"))
        except Exception as e:

            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(error_type)
            LOG.error(error_value)
            for tb in tb_list:
                LOG.error(tb)

            LOG.error(e.message)

            raise e
        # Todo: (sampath) correct the exceptions catching
        # Insert to notification_list DB.

        try:
            msg = "Do add_notification_list."
            LOG.info(msg)
            result = dbapi.add_notification_list(
                session,
                create_at=create_at,
                update_at=update_at,
                delete_at=delete_at,
                deleted=deleted,
                notification_id=jsonData.get("id"),
                notification_type=jsonData.get("type"),
                notification_regionID=jsonData.get("regionID"),
                notification_hostname=jsonData.get("hostname"),
                notification_uuid=jsonData.get("uuid"),
                notification_time=notification_time,
                notification_eventID=jsonData.get("eventID"),
                notification_eventType=jsonData.get("eventType"),
                notification_detail=jsonData.get("detail"),
                notification_startTime=notification_startTime,
                notification_endTime=j_endTime,
                notification_tzname=jsonData.get("tzname"),
                notification_daylight=jsonData.get("daylight"),
                notification_cluster_port=jsonData.get("cluster_port"),
                progress=progress,
                recover_by=recover_by,
                iscsi_ip=iscsi_ip,
                controle_ip=controle_ip,
                recover_to=recover_to
            )
            msg = "Succeeded in add_notification_list. " \
                + "Return_value = " + str(result)
            LOG.info(msg)

            msg = "Do get_all_reserve_list_by_hostname_not_deleted."
            LOG.info(msg)
            cnt = dbapi.get_all_reserve_list_by_hostname_not_deleted(
                session,
                jsonData.get("hostname")
            )
            msg = "Succeeded in get_all_reserve_list_by_hostname_not_deleted. " \
                + "Return_value = " + str(cnt)
            LOG.info(msg)

            if len(cnt) > 0:
                msg = "Do update_reserve_list_by_hostname_as_deleted."
                LOG.info(msg)
                dbapi.update_reserve_list_by_hostname_as_deleted(
                    session,
                    jsonData.get("hostname"),
                    datetime.datetime.now()
                )
                msg = "Succeeded in " \
                    + "update_reserve_list_by_hostname_as_deleted."
                LOG.info(msg)

            ret_dic = {
                "create_at": create_at,
                "update_at": update_at,
                "delete_at": delete_at,
                "deleted": deleted,
                "notification_id": jsonData.get("id"),
                "notification_type": jsonData.get("type"),
                "notification_regionID": jsonData.get("regionID"),
                "notification_hostname": jsonData.get("hostname"),
                "notification_uuid": jsonData.get("uuid"),
                "notification_time": jsonData.get("time"),
                "notification_eventID": jsonData.get("eventID"),
                "notification_eventType": jsonData.get("eventType"),
                "notification_detail": jsonData.get("detail"),
                "notification_startTime": jsonData.get("startTime"),
                "notification_endTime": j_endTime,
                "notification_tzname": jsonData.get("tzname"),
                "notification_daylight": jsonData.get("daylight"),
                "notification_cluster_port": jsonData.get("cluster_port"),
                "progress": progress,
                "recover_by": recover_by,
                "iscsi_ip": iscsi_ip,
                "controle_ip": controle_ip,
                "recover_to": recover_to
            }

            return ret_dic

        except Exception as e:

            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(error_type)
            LOG.error(error_value)
            for tb in tb_list:
                LOG.error(tb)

            LOG.error(e.message)

            raise e

    @log_process_begin_and_end.output_log
    def _get_reserve_node_from_reserve_list_db(self,
                                               cluster_port,
                                               notification_hostname,
                                               session):
        """
        Get reserve node, check it in use and change to 'enable'.
        :param: con_args: args database connection.
        :param: cluster_port: select keys, cluster port number.
        :param :cursor: cursor object
        :return: hostname: Host name of the spare node machine
                            (obtained from the spare node list table)

        """

        try:
            # Todo(sampath): write the test codes
            #                Check it
            msg = "Do get_one_reserve_list_by_cluster_port_for_update."
            LOG.info(msg)
            cnt = dbapi.get_one_reserve_list_by_cluster_port_for_update(
                session,
                cluster_port,
                notification_hostname
            )
            msg = "Succeeded in get_one_reserve_list_by_cluster_port_for_update. " \
                + "Return_value = " + str(cnt)
            LOG.info(msg)

            if not cnt:
                msg = "The reserve node not exist in reserve_list DB."
                LOG.warning(msg)
                hostname = None
            if not isinstance(cnt, (list, tuple)):
                hostname = cnt.hostname

        except Exception as e:

            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(error_type)
            LOG.error(error_value)
            for tb in tb_list:
                LOG.error(tb)

            LOG.error(e.message)

            raise e

        return hostname

    @log_process_begin_and_end.output_log
    def update_notification_list_db(self, session, key, value,
                                    notification_id):
        """
        Notification list table update
        :param :key: Update column name
        :param :value: Updated value
        :param :notification_id: Notification ID
                (updated narrowing condition of notification list table)
        """
        try:
            # Update progress with update_at and delete_at
            now = datetime.datetime.now()
            update_val = {'update_at': now}
            if key == 'progress':
                update_val['progress'] = value
                update_val['delete_at'] = now
            # Updated than progress
            else:
                if hasattr(NotificationList, key):
                    update_val[key] = value
                else:
                    raise AttributeError
            msg = "Do update_notification_list_dict."
            LOG.info(msg)
            dbapi.update_notification_list_dict(
                session, notification_id, update_val)
            msg = "Succeeded in update_notification_list_dict."
            LOG.info(msg)

        except AttributeError:
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(error_type)
            LOG.error(error_value)
            for tb in tb_list:
                LOG.error(tb)

            msg = "Exception : %s is not in attribute of \
            NotificationList" % (key)
            LOG.error(msg)
            raise AttributeError

        except exc.SQLAlchemyError:

            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(error_type)
            LOG.error(error_value)
            for tb in tb_list:
                LOG.error(tb)

            msg = "Exception : SQLAlchemy.Error in \
            update_notification_list_db()."
            LOG.error(msg)

            raise exc.SQLAlchemyError

        except KeyError:

            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(error_type)
            LOG.error(error_value)
            for tb in tb_list:
                LOG.error(tb)

            msg = "Exception : KeyError in update_notification_list_db()."
            LOG.error(msg)

            raise KeyError

    @log_process_begin_and_end.output_log
    def update_vm_list_db(self,  session, key, value, primary_id):
        """
        VM list table update
        :param :key: Update column name
        :param :value: Updated value
        :param :uuid: VM of uuid (updated narrowing condition of VM list table)
        """

        try:
            # Updated progress to start
            now = datetime.datetime.now()
            update_val = {}
            if key == 'progress' and value == 1:
                update_val['update_at'] = now
                update_val['progress'] = value
            # End the progress([success:2][error:3][skipped old:4])
            elif key == 'progress':
                update_val['update_at'] = now
                update_val['progress'] = value
                update_val['delete_at'] = now
            # Update than progress
            else:
                if hasattr(VmList, key):
                    update_val[key] = value
                else:
                    raise AttributeError
            msg = "Do update_vm_list_by_id_dict."
            LOG.info(msg)
            dbapi.update_vm_list_by_id_dict(session, primary_id, update_val)
            msg = "Succeeded in update_vm_list_by_id_dict."
            LOG.info(msg)

        except AttributeError:
            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(error_type)
            LOG.error(error_value)
            for tb in tb_list:
                LOG.error(tb)

            msg = "Exception : %s is not in attribute of \
            VmList" % (key)
            LOG.error(msg)
            raise AttributeError

        except exc.SQLAlchemyError:

            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(error_type)
            LOG.error(error_value)
            for tb in tb_list:
                LOG.error(tb)

            msg = "Exception : SQLAlchemy.Error in \
            update_vm_list_by_id_dict()."
            LOG.error(msg)

            raise exc.SQLAlchemyError

        except KeyError:

            error_type, error_value, traceback_ = sys.exc_info()
            tb_list = traceback.format_tb(traceback_)
            LOG.error(error_type)
            LOG.error(error_value)
            for tb in tb_list:
                LOG.error(tb)

            msg = "Exception : KeyError in update_notification_list_db()."
            LOG.error(msg)

            raise KeyError


class RecoveryControllerUtilApi(object):

    """
    API-related utility classes related to VM recovery control
    """

    KEYSTONE_API_VERSION = '3'
    NOVA_API_VERSION = '2'

    def __init__(self, config_object):
        self.rc_config = config_object

        project_id = self._fetch_project_id()
        auth_args = {
            'auth_url': self.rc_config.conf_nova['auth_url'],
            'username': self.rc_config.conf_nova['admin_user'],
            'password': self.rc_config.conf_nova['admin_password'],
            'project_id': project_id,
            'user_domain_name': self.rc_config.conf_nova['domain'],
            'project_domain_name': self.rc_config.conf_nova['domain'],
        }

        self.auth_session = self._get_session(auth_args)

        conf_dic = self.rc_config.get_value('recover_starter')
        api_retries = conf_dic.get('api_max_retry_cnt')

        self.nova_client = nova_client.Client(self.NOVA_API_VERSION,
                                              session=self.auth_session,
                                              connect_retries=api_retries,
                                              logger=LOG.logger)

    def _get_session(self, auth_args):
        """ Return Keystone API session object."""
        loader = loading.get_plugin_loader('password')
        auth = loader.load_from_options(**auth_args)
        sess = session.Session(auth=auth)

        return sess

    def _fetch_project_id(self):
        auth_args = {
            'auth_url': self.rc_config.conf_nova['auth_url'],
            'username': self.rc_config.conf_nova['admin_user'],
            'password': self.rc_config.conf_nova['admin_password'],
            'project_name': self.rc_config.conf_nova['project_name'],
            'project_domain_name': self.rc_config.conf_nova['domain'],
            'user_domain_name': self.rc_config.conf_nova['domain'],
        }
        sess = self._get_session(auth_args)

        ks_client = keystone_client.Client(self.KEYSTONE_API_VERSION,
                                           session=sess)
        project_name = self.rc_config.conf_nova['project_name']
        projects = filter(lambda x: (x.name == project_name),
                          ks_client.projects.list())

        if len(projects) != 1:
            msg = ("Project name: %s doesn't exist in project list."
                   % self.rc_config.conf_nova['project_name'])
            raise KeyError(msg)

        return projects[0].id

    def do_instance_show(self, uuid):
        """Returns Server Intance.

        :uuid : Instance id
        :return : Server instance
        """
        try:
            msg = ('Call Server Details API with %s' % uuid)
            LOG.info(msg)
            server = self.nova_client.servers.get(uuid)

        except exceptions.ClientException as e:
            msg = 'Fails to call Nova get Server Details API: %s' % e
            LOG.error(msg)

            raise

        return server

    def do_instance_stop(self, uuid):
        """Call Nova instance stop API.

        :param :uuid : Instance id
        :return : None if succeed
        """
        try:
            msg = ('Call Stop API with %s' % uuid)
            LOG.info(msg)
            self.nova_client.servers.stop(uuid)

        except exceptions.Conflict as e:
            msg = "Server instance %s is already in stopped." % uuid
            error_msg = "Original Nova client's error: %e" % e
            LOG.error(msg + error_msg)
            raise EnvironmentError(msg)

        except exceptions.ClientException as e:
            msg = 'Fails to call Nova Server Stop API: %s' % e
            LOG.error(msg)
            raise

    def do_instance_start(self, uuid):
        """Call Nova instance start API.

        :uuid : Instance id
        :return : None if succeed
        """
        try:
            msg = ('Call Start API with %s' % uuid)
            LOG.info(msg)
            self.nova_client.servers.start(uuid)

        except exceptions.Conflict as e:
            msg = "Server instance %s is already in active." % uuid
            error_msg = "Original Nova client's error: %e" % e
            LOG.error(msg + error_msg)
            raise EnvironmentError(msg)

        except exceptions.ClientException as e:
            msg = 'Fails to call Nova Server Start API: %s' % e
            LOG.error(msg)
            raise

    def do_instance_reset(self, uuid, status):
        """ Call Nova reset state API.

        :uuid : Instance id
        :status : Status reset to
        """
        try:
            msg = ('Call Reset State API with %s to %s' %
                   (uuid, status))
            LOG.info(msg)
            self.nova_client.servers.reset_state(uuid, status)

        except exceptions.ClientException as e:
            msg = 'Fails to call Nova Server Reset State API: %s' % e
            LOG.error(msg)
            raise EnvironmentError(msg)

    def fetch_servers_on_hypervisor(self, hypervisor):
        """Fetch server instance list on the hypervisor.

        :hypervisor : hypervisor's hostname
        :return : A list of servers
        """
        opts = {
            'host': hypervisor,
            'all_tenants': True,
        }
        try:
            msg = ('Fetch Server list on %s' % hypervisor)
            LOG.info(msg)
            servers = self.nova_client.servers.list(detailed=False,
                                                    search_opts=opts)

            return [s.id for s in servers]

        except exceptions.ClientException as e:
            msg = 'Fails to call Nova Servers List API: %s' % e
            LOG.error(msg)
            raise

    def disable_host_status(self, hostname):
        """Disable host' status.

        :hostname: Target host name
        """
        try:
            msg = ('Disable nova-compute on %s' % hostname)
            LOG.info(msg)
            self.nova_client.services.disable(hostname, 'nova-compute')

        except exceptions.ClientException as e:
            msg = 'Fails to disable nova-compute on %s: %s' % (hostname, e)
            LOG.error(msg)
            raise

    def do_instance_evacuate(self, uuid, targethost):
        """Call evacuate API for server instance.

        :uuid : Instance id
        :targethost: The name or ID of the host where the server is evacuated.
        """
        try:
            msg = ('Call Evacuate API with %s to %s' %
                   (uuid, targethost))
            LOG.info(msg)
            self.nova_client.servers.evacuate(uuid, host=targethost,
                                              on_shared_storage=True)

        except exceptions.ClientException as e:
            msg = ('Fails to call Instance Evacuate API onto %s: %s'
                   % (targethost, e))
            LOG.error(msg)
            raise
