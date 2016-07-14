# Copyright(c) 2016 Nippon Telegraph and Telephone Corporation
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
Definition of interfaces to access database and helper methods
 to handle SQLAlchemy session
"""

from sqlalchemy import engine, create_engine, or_
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import desc
from models import NotificationList, VmList, ReserveList
from models import Base
from sqlalchemy_utils.functions import database_exists, create_database
from sqlalchemy import asc
from sqlalchemy.orm import scoped_session
from sqlalchemy import distinct
import sqlalchemy.exc as dbexc
from contextlib import contextmanager
import os
import sys
import traceback
import syslog
from functools import wraps
import time
parentdir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                         os.path.pardir))
# rootdir = os.path.abspath(os.path.join(parentdir, os.path.pardir))
# project root directory needs to be add at list head rather than tail
# this file named 'masakari' conflicts to the directory name
if parentdir not in sys.path:
    sys.path = [parentdir] + sys.path

import controller.masakari_config as config
# Todo(samapth): Do not do this to import log handler
# import controller.masakari_util.RecoveryControllerUtil as util
# from controller import masari_config as config
# from controller import masakari_util as util

_SESSION = sessionmaker()


@contextmanager
def _sqlalchemy_error():
    # Todo(sampath): get the log handler and log out the error
    try:
        yield
    except dbexc.SQLAlchemyError, e:
        raise e


def _session_handle(fn):
    """Decorator to commit and safe rollback sessions if error"""

    @wraps(fn)
    def wrapped(session, *args, **kwargs):
        # session.begin(subtransactions=True)
        try:
            ret = fn(session, *args, **kwargs)
            session.commit()
            return ret
        except:
            session.rollback()
            raise
    return wrapped


def _retry_on_deadlock(fn):
    """Decorator to retry a DB API call if Deadlock was received."""
    lock_messages_error = ['Deadlock found', 'Lock wait timeout exceeded']

    @wraps(fn)
    def wrapped(*args, **kwargs):
        while True:
            try:
                return fn(*args, **kwargs)
            except dbexc.OperationalError as e:
                if any(msg in e.message for msg in lock_messages_error):
                    # msg = ("Deadlock detected when running %s Retrying..." %
                    #        (fn.__name__))
                    # rc_util.syslogout(msg, syslog.LOG_WARNING)
                    # Retry!
                    time.sleep(0.5)
                    continue
    return wrapped


def get_engine(rc_config):
    # Connect db
    conf_db_dic = rc_config.get_value('db')
    """
    Possible values for db drivername is,
     'drizzle',
     'firebird',
     'informix',
     'mssql',
     'mysql',
     'postgresql',
     'sqlite',
     'oracle',
     'sybase'
    sqlite is only for testing..
    """
    # get the drivername of the db.
    # default is sqlite
    drivername = conf_db_dic.get("drivername", "sqlite")
    charset = conf_db_dic.get("charset")
    # Todo(sampath): currently query string is only support for
    #                mysql and postgresql.
    #                need to extend the support for other dbs
    if drivername is "postgresql":
        query = {'client_encoding': charset}
    elif drivername is "mysql":
        query = {'charset': charset}
    else:
        query = {}
    if drivername != 'sqlite':
        dburl = engine.url.URL(
            drivername=drivername,
            database=conf_db_dic.get("name"),
            username=conf_db_dic.get("user"),
            password=conf_db_dic.get("passwd"),
            host=conf_db_dic.get("host"),
            port=conf_db_dic.get("port", None),
            query=query
        )
        eng = create_engine(dburl)
    else:
        eng = create_engine('sqlite:////tmp/msakari.db', echo=True)
    return eng


def create_tables():
    eng = get_engine()
    if not database_exists(eng.url):
        create_database(eng.url)
    # Create all tables in the engine
    Base.metadata.create_all(eng)


def get_session(engine):
    with _sqlalchemy_error():
        session_fac = sessionmaker(bind=engine)
        thread_local_session = scoped_session(session_fac)
    return thread_local_session()


@_session_handle
def get_all_notification_list_not_in_progress(session):
    # SELECT * FROM notification_list WHERE progress = 0
    with _sqlalchemy_error():
        res = session.query(NotificationList).filter_by(progress=0).all()
    return res


@_session_handle
def get_all_notification_list_by_notification_id(session, notification_id):
    # SELECT * FROM notification_list WHERE notification_id = :notification_id
    with _sqlalchemy_error():
        res = session.query(NotificationList).filter_by(
            notification_id=notification_id).all()
    return res


@_retry_on_deadlock
@_session_handle
def get_all_notification_list_by_id_for_update(
        session, notification_id):
    # SELECT recover_to FROM notification_list \
    #   WHERE notification_id=:notification_id for UPDATE
    return session.query(NotificationList).with_for_update().\
        filter_by(notification_id=notification_id).all()


@_session_handle
def get_all_notification_list_by_hostname_type(
        session, notification_hostname):
    # SELECT notification_time FROM notification_list \
    #   WHERE notification_hostname = :notification_hostname AND \
    #   notification_type = 'rscGroup'"
    with _sqlalchemy_error():
        res = session.query(NotificationList).\
            filter_by(notification_hostname=notification_hostname).\
            filter_by(notification_type='rscGroup').all()
    return res


@_retry_on_deadlock
@_session_handle
def add_notification_list(session, create_at, update_at,
                          delete_at, deleted,
                          notification_id, notification_type,
                          notification_regionID, notification_hostname,
                          notification_uuid, notification_time,
                          notification_eventID, notification_eventType,
                          notification_detail, notification_startTime,
                          notification_endTime, notification_tzname,
                          notification_daylight, notification_cluster_port,
                          progress, recover_by, iscsi_ip, controle_ip,
                          recover_to):
    # INSERT INTO (create_at, update_at, delete_at, deleted,
    #   notification_id, notification_type,
    #   notification_regionID, notification_hostname,
    #   notification_uuid, notification_time,
    #   notification_eventID, notification_eventType,
    #   notification_detail, notification_startTime,
    #   notification_endTime, notification_tzname,
    #   notification_daylight, notification_cluster_port,
    #   progress, recover_by, iscsi_ip, controle_ip, recover_to)
    #   VALUES (...)
    notification_list = NotificationList(
        create_at=create_at,
        update_at=update_at, delete_at=delete_at, deleted=deleted,
        notification_id=notification_id,
        notification_type=notification_type,
        notification_regionID=notification_regionID,
        notification_hostname=notification_hostname,
        notification_uuid=notification_uuid,
        notification_time=notification_time,
        notification_eventID=notification_eventID,
        notification_eventType=notification_eventType,
        notification_detail=notification_detail,
        notification_startTime=notification_startTime,
        notification_endTime=notification_endTime,
        notification_tzname=notification_tzname,
        notification_daylight=notification_daylight,
        notification_cluster_port=notification_cluster_port,
        progress=progress, recover_by=recover_by, iscsi_ip=iscsi_ip,
        controle_ip=controle_ip, recover_to=recover_to)
    session.add(notification_list)
    session.commit()
    return notification_list


@_retry_on_deadlock
@_session_handle
def update_notification_list_by_notification_id(session,
                                                notification_id, key, value):
    # UPDATE notification_list SET :key = :value
    #   WHERE notification_id = :notification_id
    res = session.query(NotificationList).\
        filter_by(notification_id=notification_id).update({key: value})
    return res


@_retry_on_deadlock
@_session_handle
def update_notification_list_by_notification_id_recover_to(
        session, notification_id, update_at, recover_to):
    # UPDATE notification_list
    #   SET update_at=:update_at, recover_to=:recover_to
    #   WHERE notification_id=:notification_id
    return session.query(NotificationList).\
        filter_by(notification_id=notification_id).\
        update({'update_at': update_at, 'recover_to': recover_to})


@_session_handle
def get_one_vm_list_by_uuid_create_at_last(session, uuid):
    # SELECT progress, create_at, retry_cnt FROM vm_list \
    #   WHERE uuid = :uuid ORDER BY create_at DESC LIMIT 1
    with _sqlalchemy_error():
        res = session.query(VmList).filter_by(uuid=uuid).order_by(
            desc(VmList.create_at)).first()
    return res


@_session_handle
def get_one_vm_list_by_uuid_and_progress_create_at_last(session,
                                                        notification_uuid):
    # SELECT * FROM vm_list WHERE uuid = :notification_uuid \
    #   AND (progress = 0 OR progress = 1) \
    #   ORDER BY create_at DESC LIMIT 1
    with _sqlalchemy_error():
        res = session.query(VmList).filter_by(uuid=notification_uuid).filter(
            or_(VmList.progress == 0, VmList.progress == 1)).order_by(
                desc(VmList.create_at)).first()
    return res


@_session_handle
def get_vm_list_by_uuid_and_progress_sorted(session, notification_uuid):
    # sql = "SELECT id, uuid FROM vm_list " \
    #       "WHERE uuid = '%s' " \
    #       "AND (progress = 0 OR progress = 1) " \
    #       "ORDER BY recover_by ASC, create_at DESC" \
    #       % (row.get("uuid"))
    with _sqlalchemy_error():
        res = session.query(VmList).filter_by(
            uuid=notification_uuid).filter(or_(
                VmList.progress == 0, VmList.progress == 1)).order_by(
                    asc(VmList.recover_by), desc(VmList.create_at)
        ).all()
    return res


@_session_handle
def get_vm_list_by_id(session, id):
    # sql = "SELECT recover_by, recover_to " \
    #               "FROM vm_list " \
    #               "WHERE id = %s" \
    #               % (primary_id)
    with _sqlalchemy_error():
        res = session.query(VmList.recover_by, VmList.recover_to).filter_by(
            id=id).one()
    return res


@_session_handle
def get_all_vm_list_by_progress(session):
    # SELECT uuid FROM vm_list WHERE progress = 0 or progress = 1
    with _sqlalchemy_error():
        res = session.query(VmList.uuid).filter(
            or_(VmList.progress == 0, VmList.progress == 1)).distinct().all()
    return res


@_retry_on_deadlock
@_session_handle
def update_vm_list_by_id_dict(session, id, update_val):
    # UPDATE vm_list SET :key = :value WHERE id = :id
    with _sqlalchemy_error():
        res = session.query(VmList).filter_by(id=id).update(update_val)
    return res


@_retry_on_deadlock
@_session_handle
def add_vm_list(session, create_at, deleted, uuid, progress, retry_cnt,
                notification_id, recover_to, recover_by):
    # INSERT INTO vm_list ( create_at, deleted, uuid, progress, retry_cnt,
    #   notification_id, recover_to, recover_by ) VALUES ( ... )
    with _sqlalchemy_error():
        vm_list = VmList(create_at=create_at, deleted=deleted, uuid=uuid,
                         progress=progress, retry_cnt=retry_cnt,
                         notification_id=notification_id,
                         recover_to=recover_to,
                         recover_by=recover_by)
    session.add(vm_list)
    session.commit()
    return vm_list


@_session_handle
def get_all_reserve_list_by_hostname_not_deleted(session, hostname):
    # SELECT * FROM reserve_list WHERE deleted=0 AND hostname=:hostname
    with _sqlalchemy_error():
        res = session.query(ReserveList).filter_by(hostname=hostname).\
            filter_by(deleted=0).all()
    return res


@_session_handle
def get_one_reserve_list_by_cluster_port_for_update(session, cluster_port,
                                                    notification_hostname):
    # SELECT id,hostname FROM reserve_list
    #   WHERE deleted=0 and cluster_port=:cluster_port
    #   and hostname!=:notification_hostname
    #   ORDER by create_at asc limit 1 FOR UPDATE
    with _sqlalchemy_error():
        res = session.query(
            ReserveList).with_for_update().filter_by(deleted=0).filter_by(
                cluster_port=cluster_port).filter(
                    ReserveList.hostname != notification_hostname).order_by(
                        asc(ReserveList.create_at)).first()
    return res


@_retry_on_deadlock
@_session_handle
def update_reserve_list_by_hostname_as_deleted(session, hostname, delete_at):
    # UPDATE reserve_list SET deleted=1, delete_at=:delete_at
    #   WHERE hostname=:hostname
    res = session.query(ReserveList).filter_by(hostname=hostname).\
        update({'delete_at': delete_at, 'deleted': 1})
    return res


@_retry_on_deadlock
@_session_handle
def update_reserve_list_by_cluster_port_as_deleted(session, delete_at,
                                                   cluster_port):
    # UPDATE reserve_list SET deleted=1, delete_at=:delete_at
    #   WHERE cluster_port=:cluster_port
    res = session.query(ReserveList).filter_by(cluster_port=cluster_port).\
        update({'delete_at': delete_at, 'deleted': 1})
    return res


@_session_handle
def get_old_records_notification(session, border_time):
    # sql = "SELECT id FROM notification_list " \
    #       "WHERE progress = 0 AND create_at < '%s'" \
    #       % (border_time_str)
    with _sqlalchemy_error():
        res = session.query(NotificationList).filter(
            NotificationList.progress == 0,
            NotificationList.create_at < border_time).all()
    return res


@_retry_on_deadlock
@_session_handle
def delete_expired_notification(session, update_at, delete_at, id):
    # sql = "UPDATE notification_list " \
    #       "SET progress = %d, update_at = '%s', delete_at = '%s' " \
    #       "WHERE id = '%s'" \
    #       % (4, datetime.datetime.now(),
    #          datetime.datetime.now(), row.get("id"))
    res = session.query(NotificationList).filter_by(
        id=id).update(
            {'progress': 4, 'update_at': update_at, 'delete_at': delete_at}
    )
    return res


@_session_handle
def get_reprocessing_records_list_distinct(session):
    # sql = "SELECT DISTINCT notification_uuid FROM notification_list " \
    #         "WHERE progress = 0 AND recover_by = 1"
    with _sqlalchemy_error():
        res = session.query(
            NotificationList.notification_uuid,).filter_by(
                progress=0).filter_by(
                recover_by=1).distinct().all()
    return res


@_session_handle
def get_reprocessing_records_list(session, notification_uuid):
    # sql = "SELECT id, notification_id, notification_hostname, "
    # "notification_uuid, notification_cluster_port, recover_by "
    # "FROM notification_list "
    # "WHERE progress = 0 AND notification_uuid = '%s' "
    # "ORDER BY create_at DESC, id DESC"
    # % (row.get("notification_uuid"))
    with _sqlalchemy_error():
        res = session.query(NotificationList).filter_by(
            progress=0).filter_by(notification_uuid=notification_uuid).order_by(
                desc(NotificationList.create_at),
                desc(NotificationList.id)).all()
    return res


@_session_handle
def get_notification_list_by_hostname(session, notification_hostname):
    # sql = "SELECT id, notification_id, notification_hostname, "
    # "notification_uuid, notification_cluster_port, recover_by "
    # "FROM notification_list "
    # "WHERE progress = 0 AND notification_hostname = '%s' "
    # "ORDER BY create_at DESC, id DESC"
    # % ("notification_hostname")
    with _sqlalchemy_error():
        res = session.query(NotificationList).filter_by(progress=0).filter_by(
            notification_hostname=notification_hostname).order_by(
                desc(NotificationList.create_at),
                desc(NotificationList.id)).all()
    return res


@_retry_on_deadlock
@_session_handle
def update_reprocessing_records(
        session, progress, update_at, delete_at, id):
    # sql = "UPDATE notification_list "
    # "SET progress = %d , update_at = '%s', "
    # "delete_at = '%s' "
    # "WHERE id = '%s'"
    # % (4, datetime.datetime.now(),datetime.datetime.now(), row2.get("id"))
    res = session.query(NotificationList).filter_by(id=id).update(
        {
            'progress': progress,
            'update_at': update_at,
            'delete_at': delete_at
        }
    )
    return res


@_session_handle
def get_notification_list_distinct_hostname(session):
    # sql = "SELECT DISTINCT notification_hostname FROM notification_list " \
    #         "WHERE progress = 0 AND recover_by = 0"
    with _sqlalchemy_error():
        res = session.query(NotificationList.notification_hostname,
                            ).filter_by(progress=0).filter_by(
                                recover_by=0).distinct().all()
    return res


@_retry_on_deadlock
@_session_handle
def update_notification_list_dict(session, notification_id, update_val):
    with _sqlalchemy_error():
        res = session.query(NotificationList).filter_by(
            notification_id=notification_id).update(update_val)
    return res


@_session_handle
def get_old_records_vm_list(session, create_at, update_at):
    # sql = "SELECT id FROM vm_list " \
    #       "WHERE (progress = 0 AND create_at < '%s') " \
    #       "OR (progress = 1 AND update_at < '%s')" \
    #       % (border_time_str, border_time_str)
    with _sqlalchemy_error():
        res = session.query(VmList).filter(
            VmList.progress == 0,
            VmList.create_at < create_at,
            VmList.update_at < update_at).all()
    return res
