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
recovery status management tool
"""

import MySQLdb
import datetime
import sys
import argparse
import subprocess

################################################################################
#
# (CLASS):recovery_status_manage
#
################################################################################

class recovery_status_manage(object):

    """
    recovery status management class
    """

################################################################################
#
# (Constructor):__init__
#
################################################################################

    def __init__(self):

        parser = argparse.ArgumentParser(prog='recovery_status_manage.py', add_help=False)

        parser.add_argument('--mode', help='list/update')
        parser.add_argument('--uuid', help='uuid')
        parser.add_argument('--db-user', help='mysql user name')
        parser.add_argument('--db-password', help='mysql user password')
        parser.add_argument('--db-host', help='mysql host name')

        args = parser.parse_args()

        #command input information check
        if self._command_input_information_check(parser,args) == "NG":
            return

        msg = "recovery status manage execution start"
        print msg

        try:

            #DB connection
            db = self._db_connect(args.db_user,
                                  args.db_password,
                                  args.db_host)

            #mode="list"
            if args.mode == "list":

                #ALL
                if args.uuid == None:

                    sysout_sql = self._recovery_status_manage_list_all(args.db_user,
                                                            args.db_password,
                                                            args.db_host,
                                                            db)

                #UUID
                else:

                    sysout_sql = self._recovery_status_manage_list_uuid(args.uuid,
                                                            args.db_user,
                                                            args.db_password,
                                                            args.db_host,
                                                            db)
            #mode="update"
            else:

                sysout_sql = self._recovery_status_manage_update(args.uuid,
                                                          args.db_user,
                                                          args.db_password,
                                                          args.db_host,
                                                          db)

            #sysout
            if sysout_sql != None:
                 subprocess.call(sysout_sql, shell=True)

        except:
            msg = "recovery status manage execution failure"
            print msg

        finally:
            msg = "recovery status manage execution end"
            print msg


################################################################################
#
# (METHOD):_command_input_information_check
#
################################################################################

    def _command_input_information_check(self,parser,args):

        result = "OK"
        #command format and input parameter check

        if (args.mode == None
         or args.db_user == None
         or args.db_password == None
         or args.db_host == None):
            result = "NG"

        if args.mode == "list":
            pass

        elif args.mode == "update":
            if args.uuid == None:
                result = "NG"

        else:
            result = "NG"

        #usage display
        if result == "NG":
            parser.print_help()

        return result

################################################################################
#
# (METHOD):_db_connect
#
################################################################################

    def _db_connect(self,
                    mysql_user_name,
                    mysql_user_password,
                    mysql_node_name):

        try:
            db = MySQLdb.connect(host=mysql_node_name,
                                 db='vm_ha',
                                 user=mysql_user_name,
                                 passwd=mysql_user_password,
                                 charset='utf8'
                                 )
            return db

        except:
            msg = "db connection failed"
            print msg
            raise


################################################################################
#
# (METHOD):_recovery_status_manage_list_all
#
################################################################################

    def _recovery_status_manage_list_all(self,
                                        mysql_user_name,
                                        mysql_user_password,
                                        mysql_node_name,
                                        db):

        # Execute SQL
        cursor = db.cursor(MySQLdb.cursors.DictCursor)

        sql = ("SELECT * FROM vm_list "
               "WHERE deleted = 0 "
               "AND (progress = 0 OR progress = 1 OR progress = 3)")

        try:
            row_cnt = cursor.execute(sql)
            if row_cnt == 0:
                msg = "none vm_list"
                print msg
                return None

            # sysout
            else:
                sql = ("mysql --host=%s --database=vm_ha "
                       "--user=%s --password=%s "
                       "-e\"SELECT "
                       "create_at,"
                       "update_at,"
                       "uuid,"
                       "progress,"
                       "notification_id,"
                       "recover_by "
                       "FROM vm_list "
                       "WHERE deleted = 0 "
                       "AND (progress = 0 OR progress = 1 OR progress = 3)\";"
                       ) % (mysql_node_name,
                            mysql_user_name,
                            mysql_user_password)

                return sql

        except:
            msg = "vm_list select(all) failed"
            print msg
            raise

        finally:
            db.commit()
            db.close()


################################################################################
#
# (METHOD):_recovery_status_manage_list_uuid
#
################################################################################

    def _recovery_status_manage_list_uuid(self,
                                          uuid,
                                          mysql_user_name,
                                          mysql_user_password,
                                          mysql_node_name,
                                          db):

        # Execute SQL
        cursor = db.cursor(MySQLdb.cursors.DictCursor)

        sql = ("SELECT * FROM vm_list "
               "WHERE uuid='%s' "
               "AND deleted = 0 "
               "AND (progress = 0 OR progress = 1 OR progress = 3)"
              ) % (uuid)

        try:

            row_cnt = cursor.execute(sql)

            if row_cnt == 0:
                msg = "none vm_list"
                print msg
                return None

            # sysout
            else:

                sql = ("mysql --host=%s --database=vm_ha "
                       "--user=%s --password=%s "
                       "-e\"SELECT "
                       "create_at,"
                       "update_at,"
                       "uuid,"
                       "progress,"
                       "notification_id,"
                       "recover_by "
                       "FROM vm_list "
                       "WHERE uuid = '%s'  "
                       "AND deleted = 0 "
                       "AND (progress = 0 OR progress = 1 OR progress = 3)\";"
                       ) % (mysql_node_name,
                            mysql_user_name,
                            mysql_user_password,
                            uuid)


                return sql

        except:
            msg = "vm_list select(uuid) failed"
            print msg
            raise

        finally:
            db.commit()
            db.close()


################################################################################
#
# (METHOD):_recovery_status_manage_update
#
################################################################################

    def _recovery_status_manage_update(self,
                                       uuid,
                                       mysql_user_name,
                                       mysql_user_password,
                                       mysql_node_name,
                                       db):

        # Execute SQL
        cursor = db.cursor(MySQLdb.cursors.DictCursor)

        sql = ("SELECT "
               "* FROM vm_list "
               "WHERE uuid='%s' AND deleted = 0 "
               "AND (progress = 0 OR progress = 1)"
              ) % (uuid)

        try:
            row_cnt = cursor.execute(sql)

            if row_cnt == 0:
                msg = "none vm_list"
                print msg
                return None

            else:
                # update
                update_at = datetime.datetime.now()
                progress = "2"
                sql = ("UPDATE vm_list "
                       "SET progress = %s ,update_at = '%s' "
                       "WHERE uuid = '%s' "
                       "AND deleted = 0 "
                       "AND (progress = 0 OR progress = 1)"
                      ) % (progress, update_at,uuid)

                cursor.execute(sql)

                # sysout
                sql = ("mysql --host=%s --database=vm_ha "
                       "--user=%s --password=%s "
                       "-e\"SELECT "
                       "create_at,"
                       "update_at,"
                       "uuid,"
                       "progress,"
                       "notification_id,"
                       "recover_by "
                       "FROM vm_list "
                       "WHERE uuid = '%s' AND update_at = '%s' "
                       "AND deleted = 0 "
                       "AND progress = 2\";"
                       ) % (mysql_node_name,
                            mysql_user_name,
                            mysql_user_password,
                            uuid,
                            update_at)

                return sql

        except:
            msg = "vm_list update failed"
            print msg
            raise

        finally:
            db.commit()
            db.close()

################################################################################

if __name__ == '__main__':

    recovery_status_manage()


##########################################################################################
#
#(command)
#
#[python recovery_status_manage.py --mode list --db-user root --db-password openstack --db-host localhost]
#[python recovery_status_manage.py --mode list --uuid DB1-UUID-0001 --db-user root --db-password openstack --db-host localhost]
#[python recovery_status_manage.py --mode update --uuid DB1-UUID-0001 --db-user root --db-password openstack --db-host localhost]
#
##########################################################################################

