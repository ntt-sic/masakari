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
This file defines the RecoveryControllerConfig class.
"""

import ConfigParser
import syslog
import MySQLdb
import paramiko
import sys
import os
import logging
import socket


class RecoveryControllerConfig(object):

    """
    RecoveryControllerConfig class:
    This class to hold the values specified in the configuration file.
    """

    def __init__(self):
        """
        Constructor:
        This constructor holds the values
        that are specified in the configuration file in the dictionary type
        for each section.
        """
        self._get_option()

    def _get_option(self):
        config_file_path = '/etc/masakari/masakari-controller.conf'

        inifile = ConfigParser.SafeConfigParser()
        inifile.read(config_file_path)

        self.conf_wsgi = {}
        self.conf_ssh = {}
        self.conf_db = {}
        self.conf_log = {}
        self.syslog_lv = {'debug': syslog.LOG_DEBUG,
                          'info': syslog.LOG_INFO,
                          'notice': syslog.LOG_NOTICE,
                          'warning': syslog.LOG_WARNING,
                          'err': syslog.LOG_ERR}
        self.config_recover_starter = {}
        self.config_nova = {}

        # insert conf_wsgi dictionary
        self.conf_wsgi = self._set_wsgi_section(inifile)

        # insert conf_db dictionary
        self.conf_db = self._set_db_section(inifile)

        # insert conf_log dictionary
        log_lv = inifile.get('log', 'log_level')
        self.conf_log['log_level'] = self.syslog_lv[log_lv]

        # insert conf_recover_starter dictionary
        self.conf_recover_starter = self._set_recover_starter_section(inifile)

        # insert conf_nova dictionary
        self.conf_nova = self._set_nova_section(inifile)

        return 0

    def _set_wsgi_section(self, inifile):
        conf_wsgi = {}
        conf_wsgi['server_port'] = inifile.get('wsgi', 'server_port')

        return conf_wsgi

    def _set_db_section(self, inifile):
        conf_db = {}
        conf_db['drivername'] = inifile.get('db', 'drivername')
        conf_db['host'] = inifile.get('db', 'host')
        conf_db['name'] = inifile.get('db', 'name')
        conf_db['user'] = inifile.get('db', 'user')
        conf_db['passwd'] = inifile.get('db', 'passwd')
        conf_db['charset'] = inifile.get('db', 'charset')
        conf_db['lock_retry_max_cnt'] = \
            inifile.get('db', 'lock_retry_max_cnt')
        conf_db['innodb_lock_wait_timeout'] = \
            inifile.get('db', 'innodb_lock_wait_timeout')

        return conf_db

    def _set_recover_starter_section(self, inifile):
        conf_recover_starter = {}
        conf_recover_starter['interval_to_be_retry'] = inifile.get(
            'recover_starter', 'interval_to_be_retry')
        conf_recover_starter['max_retry_cnt'] = inifile.get(
            'recover_starter', 'max_retry_cnt')
        conf_recover_starter['semaphore_multiplicity'] = inifile.get(
            'recover_starter', 'semaphore_multiplicity')
        conf_recover_starter['notification_time_difference'] = inifile.get(
            'recover_starter', 'notification_time_difference')
        try:
            conf_recover_starter['node_err_wait'] = inifile.get(
                'recover_starter', 'node_err_wait')
        except ConfigParser.NoOptionError:
            conf_recover_starter['node_err_wait'] = '120'

        conf_recover_starter['api_max_retry_cnt'] = inifile.get(
            'recover_starter', 'api_max_retry_cnt')
        conf_recover_starter['api_retry_interval'] = inifile.get(
            'recover_starter', 'api_retry_interval')
        conf_recover_starter['recovery_max_retry_cnt'] = inifile.get(
            'recover_starter', 'recovery_max_retry_cnt')
        conf_recover_starter['recovery_retry_interval'] = inifile.get(
            'recover_starter', 'recovery_retry_interval')
        conf_recover_starter['api_check_interval'] = inifile.get(
            'recover_starter', 'api_check_interval')
        conf_recover_starter['api_check_max_cnt'] = inifile.get(
            'recover_starter', 'api_check_max_cnt')
        conf_recover_starter['notification_expiration_sec'] = \
            inifile.get('recover_starter', 'notification_expiration_sec')

        return conf_recover_starter

    def _set_nova_section(self, inifile):
        conf_nova = {}
        conf_nova['domain'] = inifile.get('nova', 'domain')
        conf_nova['admin_user'] = inifile.get('nova', 'admin_user')
        conf_nova['admin_password'] = inifile.get('nova', 'admin_password')
        conf_nova['auth_url'] = inifile.get('nova', 'auth_url')
        conf_nova['project_name'] = inifile.get('nova', 'project_name')

        return conf_nova

    def get_value(self, section):
        """
        Return the value
        that is set for the specified section in the argument as a dictionary
        type.
        :param section: The section that exists in the configuration file.
        :returns dict: The value that is set for the specified section in the
         argument.
        """
        if section == 'wsgi':
            return self.conf_wsgi
        elif section == 'db':
            return self.conf_db
        elif section == 'log':
            return self.conf_log
        elif section == 'recover_starter':
            return self.conf_recover_starter
        elif section == 'nova':
            return self.conf_nova
        else:
            dicNull = {}
            return dicNull
