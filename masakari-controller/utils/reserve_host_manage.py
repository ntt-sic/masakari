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
Spare host list registration tool
"""

import MySQLdb
import datetime
import argparse
import subprocess

################################################################################
#
# (CLASS):reserve_host_manage
#
################################################################################

class reserve_host_manage(object):

    """
    Spare host list registration class
    """


################################################################################
#
# (Constructor):__init__
#
################################################################################

    def __init__(self):

        parser = argparse.ArgumentParser(prog='reserve_host_manage.py', add_help=False)

        parser.add_argument('--mode', help='add/update/delete/list')
        parser.add_argument('--port', help='cluster_port')
        parser.add_argument('--host', help='hostname')
        parser.add_argument('--before-host', help='Change before the host name')
        parser.add_argument('--after-host', help='Change after the host name')
        parser.add_argument('--db-user', help='mysql user name')
        parser.add_argument('--db-password', help='mysql user password')
        parser.add_argument('--db-host', help='mysql host name')

        args = parser.parse_args()

        #command input information check
        if self._command_input_information_check(parser,args) == "NG":
            return

        msg = "reserve_host_manage execution start"
        print msg

        try:

            #DB connection
            db = self._db_connect(args.db_user,
                                  args.db_password,
                                  args.db_host)

            #mode sorting
            #mode="add"
            if args.mode == "add":
                sysout_sql = self._reserve_host_add(args.port,
                                                    args.host,
                                                    args.db_user,
                                                    args.db_password,
                                                    args.db_host,
                                                    db)

            #mode="update"
            elif args.mode == "update":
                 sysout_sql = self._reserve_host_update(args.port,
                                                        args.before_host,
                                                        args.after_host,
                                                        args.db_user,
                                                        args.db_password,
                                                        args.db_host,
                                                        db)

            #mode="delete"
            elif args.mode == "delete":
                sysout_sql = self._reserve_host_delete(args.port,
                                                       args.host,
                                                       args.db_user,
                                                       args.db_password,
                                                       args.db_host,
                                                       db)


            #mode="list"
            else:
                #ALL
                if args.port == None:
                    sysout_sql = self._reserve_host_list_all(args.db_user,
                                                             args.db_password,
                                                             args.db_host,
                                                             db)

                #PORT
                else:
                    sysout_sql = self._reserve_host_list_port(args.port,
                                                              args.db_user,
                                                              args.db_password,
                                                              args.db_host,
                                                              db)

            #sysout
            if sysout_sql != None:
                 subprocess.call(sysout_sql, shell=True)

        except:
            msg = "reserve_host_manage execution failure"
            print msg

        finally:
            msg = "reserve_host_manage execution end"
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

        if args.mode == "add":
            if (args.port == None
             or args.host == None
             or args.before_host != None
             or args.after_host != None):
                result = "NG"

        elif args.mode == "update":
            if (args.port == None
             or args.before_host == None
             or args.after_host == None
             or args.host != None):
                result = "NG"

        elif args.mode == "delete":
            if (args.port == None
             or args.host == None
             or args.before_host != None
             or args.after_host != None):
                result = "NG"

        elif args.mode == "list":
            if (args.host != None
             or args.before_host != None
             or args.after_host != None):
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
                    mysql_host_name):

        try:
            db = MySQLdb.connect(host=mysql_host_name,
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
# (METHOD):_reserve_host_add
#
################################################################################

    def _reserve_host_add(self,
                          port_number,
                          host_name,
                          mysql_user_name,
                          mysql_user_password,
                          mysql_host_name,
                          db):

        # Execute SQL
        cursor = db.cursor(MySQLdb.cursors.DictCursor)

        sql = (("select * "
                "from reserve_list "
                "where cluster_port = '%s' "
                "AND hostname ='%s' "
                "AND deleted = 0") % (port_number, host_name))

        try:

            row_cnt = cursor.execute(sql)

            if row_cnt > 0:
                msg = "host is already registered"
                print msg
                return

            # INSERT
            else:
                create_at = datetime.datetime.now()
                deleted = "0"
                cluster_port = port_number
                hostname = host_name

                sql = ("INSERT INTO reserve_list "
                       "( create_at, deleted, cluster_port, hostname ) "
                       "VALUES ( '%s', %s, '%s', '%s' )" % (create_at,
                                                        deleted,
                                                        cluster_port,
                                                        hostname))

                cursor.execute(sql)

                sql = ("mysql --host=%s --database=vm_ha "
                       "--user=%s --password=%s "
                       "-e\"SELECT "
                       "create_at,"
                       "deleted,"
                       "cluster_port,"
                       "hostname "
                       "FROM reserve_list "
                       "WHERE deleted = 0 "
                       "AND cluster_port = '%s' "
                       "AND hostname = '%s' "
                       "AND create_at = '%s'\";"
                       ) % (mysql_host_name,
                            mysql_user_name,
                            mysql_user_password,
                            port_number,
                            host_name,
                            create_at)

                return sql

        except:
            msg = "db insert failed"
            print msg
            raise

        finally:
            db.commit()
            db.close()

################################################################################
#
# (METHOD):_reserve_host_update
#
################################################################################

    def _reserve_host_update(self,
                             port_number,
                             before_host_name,
                             after_host_name,
                             mysql_user_name,
                             mysql_user_password,
                             mysql_host_name,
                             db):

        # Execute SQL
        cursor = db.cursor(MySQLdb.cursors.DictCursor)

        sql_before = (("select * "
                       "from reserve_list "
                       "where cluster_port = '%s' "
                       "AND hostname = '%s' "
                       "AND deleted = 0"
                       ) % (port_number,before_host_name))

        sql_after = (("select * "
                       "from reserve_list "
                       "where cluster_port = '%s' "
                       "AND hostname = '%s' "
                       "AND deleted = 0"
                       ) % (port_number,after_host_name))

        try:

            row_cnt = cursor.execute(sql_before)

            if row_cnt == 0:
                msg = "none updated host"
                print msg
                return

            # UPDATE
            else:

                row_cnt = cursor.execute(sql_after)

                if row_cnt > 0:
                    msg = "host is already registered"
                    print msg
                    return

                update_at = datetime.datetime.now()
                deleted = "0"
                cluster_port = port_number

                sql = ("UPDATE reserve_list "
                       "SET hostname = '%s' ,update_at = '%s' "
                       "WHERE cluster_port = '%s' "
                       "AND hostname = '%s' "
                       "AND deleted = 0"
                       ) % (after_host_name,
                            update_at,
                            port_number,
                            before_host_name)

                cursor.execute(sql)

                sql = ("mysql --host=%s --database=vm_ha "
                       "--user=%s --password=%s "
                       "-e\"SELECT "
                       "update_at,"
                       "deleted,"
                       "cluster_port,"
                       "hostname "
                       "FROM reserve_list "
                       "WHERE deleted = 0 "
                       "AND cluster_port = '%s' "
                       "AND hostname = '%s' "
                       "AND update_at = '%s'\";"
                       ) % (mysql_host_name,
                            mysql_user_name,
                            mysql_user_password,
                            port_number,
                            after_host_name,
                            update_at)

                return sql

        except:
            msg = "db update failed"
            print msg
            raise

        finally:
            db.commit()
            db.close()


################################################################################
#
# (METHOD):_reserve_host_delete
#
################################################################################


    def _reserve_host_delete(self,
                             port_number,
                             host_name,
                             mysql_user_name,
                             mysql_user_password,
                             mysql_host_name,db):

        # Execute SQL
        cursor = db.cursor(MySQLdb.cursors.DictCursor)

        sql = (("select * "
                "from reserve_list "
                "where cluster_port = '%s' "
                "AND hostname ='%s' "
                "AND deleted = 0") % (port_number, host_name))

        try:

            row_cnt = cursor.execute(sql)

            if row_cnt == 0:
                msg = "none deleted host"
                print msg
                return

            # DELETE
            else:
                delete_at = datetime.datetime.now()
                deleted = "1"
                cluster_port = port_number

                sql = ("UPDATE reserve_list "
                       "SET deleted=1,delete_at = '%s' "
                       "WHERE cluster_port = '%s' "
                       "AND hostname = '%s' "
                       "AND deleted = 0"
                      ) % (delete_at,
                           port_number,
                           host_name)

                cursor.execute(sql)

                sql = ("mysql --host=%s --database=vm_ha "
                       "--user=%s --password=%s "
                       "-e\"SELECT "
                       "delete_at,"
                       "deleted,"
                       "cluster_port,"
                       "hostname "
                       "FROM reserve_list "
                       "WHERE deleted = 1 "
                       "AND cluster_port = '%s' "
                       "AND hostname = '%s' "
                       "AND delete_at = '%s'\";"
                       ) % (mysql_host_name,
                            mysql_user_name,
                            mysql_user_password,
                            port_number,
                            host_name,
                            delete_at)

                return sql

        except:
            msg = "db delete failed"
            print msg
            raise

        finally:
            db.commit()
            db.close()

################################################################################
#
# (METHOD):_reserve_host_list_all
#
################################################################################

    def _reserve_host_list_all(self,
                               mysql_user_name,
                               mysql_user_password,
                               mysql_host_name,
                               db):

        # Execute SQL
        cursor = db.cursor(MySQLdb.cursors.DictCursor)

        sql = ("select * "
                "from reserve_list "
                "where deleted = 0 "
                )

        try:

            row_cnt = cursor.execute(sql)

            if row_cnt == 0:
                msg = "none selected host"
                print msg
                return

            result = cursor.fetchall()

            sql = ("mysql --host=%s --database=vm_ha "
                   "--user=%s --password=%s "
                   "-e\"SELECT "
                   "create_at,"
                   "update_at,"
                   "delete_at,"
                   "deleted,"
                   "cluster_port,"
                   "hostname "
                   "FROM reserve_list "
                   "WHERE deleted = 0 \";"
                  ) % (mysql_host_name,
                       mysql_user_name,
                       mysql_user_password,
                      )

            return sql

        except:
            msg = "db select failed"
            print msg
            raise

        finally:
            db.close()

################################################################################
#
# (METHOD):_reserve_host_list_port
#
################################################################################

    def _reserve_host_list_port(self,
                           port_number,
                           mysql_user_name,
                           mysql_user_password,
                           mysql_host_name,
                           db):

        # Execute SQL
        cursor = db.cursor(MySQLdb.cursors.DictCursor)

        sql = ("select * "
                "from reserve_list "
                "where cluster_port = '%s' "
                "AND deleted = 0"
               ) % (port_number)

        try:

            row_cnt = cursor.execute(sql)

            if row_cnt == 0:
                msg = "none selected host"
                print msg
                return

            result = cursor.fetchall()

            sql = ("mysql --host=%s --database=vm_ha "
                   "--user=%s --password=%s "
                   "-e\"SELECT "
                   "create_at,"
                   "update_at,"
                   "delete_at,"
                   "deleted,"
                   "cluster_port,"
                   "hostname "
                   "FROM reserve_list "
                   "WHERE deleted = 0 "
                   "AND cluster_port = '%s'\";"
                  ) % (mysql_host_name,
                       mysql_user_name,
                       mysql_user_password,
                       port_number
                      )

            return sql

        except:
            msg = "db select failed"
            print msg
            raise

        finally:
            db.close()

################################################################################

if __name__ == '__main__':

    reserve_host_manage()

##########################################################################################
#
#(command sample)
#[python reserve_host_manage.py --mode add --port 1111 --host devstack01 --db-user root --db-password openstack --db-host localhost]
#[python reserve_host_manage.py --mode update --port 1111 --before-host devstack01 --after-host devstack02 --db-user root --db-password openstack --db-host localhost]
#[python reserve_host_manage.py --mode delete --port 1111 --host devstack01 --db-user root --db-password openstack --db-host localhost]
#[python reserve_host_manage.py --mode list --db-user root --db-password openstack --db-host localhost]
#[python reserve_host_manage.py --mode list --port 1111 --db-user root --db-password openstack --db-host localhost]
#
##########################################################################################

