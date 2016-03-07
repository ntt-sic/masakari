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

from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import desc
from models import NotificationList, VmList, ReserveList
from sqlalchemy import asc
import controller.masakari_config as config
from sqlalchemy.orm import scoped_session

_SESSION = sessionmaker()


def get_engine():
    rc_config = config.RecoveryControllerConfig()
    # Connect db
    conf_db_dic = rc_config.get_value('db')
    # URL looks like this, "mysql://scott:tiger@localhost/test?charset=utf8"
    url = 'mysql://'\
          + conf_db_dic.get("user") + ':' + conf_db_dic.get("passwd") +\
          '@' + conf_db_dic.get("host") +\
          '/' + conf_db_dic.get("name") +\
          '?' + 'charset=' + conf_db_dic.get("charset")
    engine = create_engine(url)
    return engine


def get_session(engine):
    session_fac = sessionmaker(bind=engine)
    thread_local_session = scoped_session(session_fac)
    return thread_local_session()


def get_all_notification_list_not_in_progress(session):
    # SELECT * FROM notification_list WHERE progress = 0
    return session.query(NotificationList).filter_by(progress=0).all()


def get_all_notification_list_by_notification_id(session, notification_id):
    # SELECT * FROM notification_list WHERE notification_id = :notification_id
    return session.query(NotificationList).\
        filter_by(notification_id=notification_id).all()


def get_all_notification_list_by_notification_id_for_update(
        session, notification_id):
    # SELECT recover_to FROM notification_list \
    #   WHERE notification_id=:notification_id for UPDATE
    return session.query(NotificationList).with_for_update().\
        filter_by(notification_id=notification_id).all()


def get_all_notification_list_by_hostname_with_rscgroup_type(
        session, notification_hostname):
    # SELECT notification_time FROM notification_list \
    #   WHERE notification_hostname = :notification_hostname AND \
    #   notification_type = 'rscGroup'"
    return session.query(NotificationList).\
        filter_by(notification_hostname=notification_hostname).\
        filter_by(notification_type='rscGroup').all()


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
    return notification_list


def update_notification_list_by_notification_id(session,
                                                notification_id, key, value):
    # UPDATE notification_list SET :key = :value
    #   WHERE notification_id = :notification_id
    return session.query(NotificationList).\
        filter_by(notification_id=notification_id).update({key: value})


def update_notification_list_by_notification_id_set_recover_to(
        session, notification_id, update_at, recover_to):
    # UPDATE notification_list
    #   SET update_at=:update_at, recover_to=:recover_to
    #   WHERE notification_id=:notification_id
    return session.query(NotificationList).\
        filter_by(notification_id=notification_id).\
        update({'update_at': update_at, 'recover_to': recover_to})


def get_one_vm_list_by_uuid_create_at_last(session, uuid):
    # SELECT progress, create_at, retry_cnt FROM vm_list \
    #   WHERE uuid = :uuid ORDER BY create_at DESC LIMIT 1
    return session.query(VmList).filter_by(uuid=uuid).order_by(
        desc(VmList.create_at)).first()


def get_one_vm_list_by_uuid_and_progress_create_at_last(session,
                                                        notification_uuid):
    # SELECT * FROM vm_list WHERE uuid = :notification_uuid \
    #   AND (progress = 0 OR progress = 1) \
    #   ORDER BY create_at DESC LIMIT 1
    return session.query(VmList).filter_by(uuid=notification_uuid).filter(
        or_(VmList.progress == 0, VmList.progress == 1)).order_by(
            desc(VmList.create_at)).first()


def get_all_vm_list_by_progress(session):
    # SELECT uuid FROM vm_list WHERE progress = 0 or progress = 1
    return session.query(VmList).filter(
        or_(VmList.progress == 0, VmList.progress == 1)).all()


def update_vm_list_by_id(session, id, key, value):
    # UPDATE vm_list SET :key = :value WHERE id = :id
    return session.query(VmList).filter_by(id=id).update({key: value})


def add_vm_list(session, create_at, deleted, uuid, progress, retry_cnt,
                notification_id, recover_to, recover_by):
    # INSERT INTO vm_list ( create_at, deleted, uuid, progress, retry_cnt,
    #   notification_id, recover_to, recover_by ) VALUES ( ... )
    vm_list = VmList(create_at=create_at, deleted=deleted, uuid=uuid,
                     progress=progress, retry_cnt=retry_cnt,
                     notification_id=notification_id, recover_to=recover_to,
                     recover_by=recover_by)
    session.add(vm_list)
    return vm_list


def get_all_reserve_list_by_hostname_not_deleted(session, hostname):
    # SELECT * FROM reserve_list WHERE deleted=0 AND hostname=:hostname
    return session.query(ReserveList).filter_by(hostname=hostname).\
        filter_by(deleted=0).all()


def get_one_reserve_list_by_cluster_port_for_update(session, cluster_port,
                                                    notification_hostname):
    # SELECT id,hostname FROM reserve_list
    #   WHERE deleted=0 and cluster_port=:cluster_port
    #   and hostname!=:notification_hostname
    #   ORDER by create_at asc limit 1 FOR UPDATE
    return session.query(
        ReserveList).with_for_update().filter_by(deleted=0).filter_by(
        cluster_port=cluster_port).filter(
            ReserveList.hostname != notification_hostname).order_by(
                asc(ReserveList.create_at)).first()


def update_reserve_list_by_hostname_as_deleted(session, hostname, delete_at):
    # UPDATE reserve_list SET deleted=1, delete_at=:delete_at
    #   WHERE hostname=:hostname
    return session.query(ReserveList).filter_by(hostname=hostname).\
        update({'delete_at': delete_at, 'deleted': 1})


def update_reserve_list_by_cluster_port_as_deleted(session, delete_at,
                                                   cluster_port):
    # UPDATE reserve_list SET deleted=1, delete_at=:delete_at
    #   WHERE cluster_port=:cluster_port
    return session.query(ReserveList).filter_by(cluster_port=cluster_port).\
        update({'delete_at': delete_at, 'deleted': 1})
