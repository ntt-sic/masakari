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
VM-HA data management tool
"""

import MySQLdb
import datetime
import argparse
import ConfigParser

################################################################################
#
# (CLASS):vmha_data_manage
#
################################################################################

class vmha_data_manage(object):

    """
    VM-HA data management class
    """

################################################################################
#
# (Constructor):__init__
#
################################################################################

    def __init__(self):

        parser = argparse.ArgumentParser(prog='vmha_data_manage.py', add_help=False)

        parser.add_argument('--mode', help='delete')

        args = parser.parse_args()

        #command input information check
        if self._command_input_information_check(parser,args) == "NG":
            return

        try:

            config_file_path = '/etc/recovery_controller/recovery_controller.conf'
            inifile = ConfigParser.SafeConfigParser()
            inifile.read(config_file_path)


            #DB connection
            db = self._db_connect(inifile)

            #mode="delete"
            period = int(30)
            try:
                period = int(inifile.get('vmha_data_manage', 'period'))
            except:
                pass

            self._vmha_data_manage_delete(period,
                                          db)

        except:
            pass


################################################################################
#
# (METHOD):_command_input_information_check
#
################################################################################

    def _command_input_information_check(self,parser,args):

        result = "OK"
        #command format and input parameter check

        if (args.mode == None):
            result = "NG"

        if args.mode != "delete":
            result = "NG"

        return result

################################################################################
#
# (METHOD):_db_connect
#
################################################################################


    def _db_connect(self,inifile):

        try:

            db_host = inifile.get('db', 'host')

            db_name = inifile.get('db', 'name')
            db_user = inifile.get('db', 'user')
            db_passwd = inifile.get('db', 'passwd')
            db_charset = inifile.get('db', 'charset')

            db = MySQLdb.connect(host=db_host,
                                 db=db_name,
                                 user=db_user,
                                 passwd=db_passwd,
                                 charset=db_charset
                                 )

            return db

        except:
            raise


################################################################################
#
# (METHOD):_vmha_data_manage_delete
#
################################################################################

    def _vmha_data_manage_delete(self,
                                 period,
                                 db):

        today = datetime.datetime.now()
        deadline = today - datetime.timedelta(days=(period+1))

        # Execute SQL
        cursor = db.cursor(MySQLdb.cursors.DictCursor)

        try:

            # delete(reserve_list)
            sql = ("DELETE FROM reserve_list "
                   "WHERE deleted = 1 "
                   "AND delete_at < '%s'"
                  ) % (deadline)

            cursor.execute(sql)

            # delete(notification_list)
            sql = ("DELETE FROM notification_list "
                   "WHERE delete_at IS NOT NULL "
                   "AND delete_at != '0000-00-00 00:00:00' "
                   "AND delete_at < '%s'"
                  ) % (deadline)

            cursor.execute(sql)

            # delete(vm_list)
            sql = ("DELETE FROM vm_list "
                   "WHERE delete_at IS NOT NULL "
                   "AND delete_at != '0000-00-00 00:00:00' "
                   "AND delete_at < '%s'"
                  ) % (deadline)

            cursor.execute(sql)

        except:
            raise

        finally:
            db.commit()
            db.close()

################################################################################

if __name__ == '__main__':

    vmha_data_manage()


##########################################################################################
#
#(command)
#
#[python vmha_data_manage.py --mode delete]
#
##########################################################################################

