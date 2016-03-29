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
SQLAlchemy model for masakari data.
"""
from sqlalchemy import Column, Integer, DateTime, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class HasId(object):
    id = Column(Integer, primary_key=True, autoincrement=True)


class HasAudit(object):
    create_at = Column(DateTime)
    update_at = Column(DateTime)
    delete_at = Column(DateTime)
    deleted = Column(Integer)


class NotificationList(Base, HasId, HasAudit):
    """ Represents a notification sent from monitors """

    __tablename__ = 'notification_list'

    notification_id = Column(String(256))
    notification_type = Column(String(16))
    notification_regionID = Column(String(256))
    notification_hostname = Column(String(256))
    notification_uuid = Column(String(256))
    notification_time = Column(DateTime)
    notification_eventID = Column(String(1))
    notification_eventType = Column(String(1))
    notification_detail = Column(String(2))
    notification_startTime = Column(DateTime)
    notification_endTime = Column(DateTime)
    notification_tzname = Column(String(16))
    notification_daylight = Column(String(1))
    notification_cluster_port = Column(String(64))
    progress = Column(Integer)
    recover_by = Column(Integer)
    iscsi_ip = Column(String(16))
    controle_ip = Column(String(16))
    recover_to = Column(String(256))


class VmList(Base, HasId, HasAudit):
    """ Represents a nova instance to recovery from failures """

    __tablename__ = 'vm_list'

    uuid = Column(String(64))
    progress = Column(Integer)
    retry_cnt = Column(Integer)
    notification_id = Column(String(256))
    recover_to = Column(String(256))
    recover_by = Column(Integer)


class ReserveList(Base, HasId, HasAudit):
    """ Represents a hypervisor reserved for failure handling """
    __tablename__ = 'reserve_list'

    cluster_port = Column(String(64))
    hostname = Column(String(256))