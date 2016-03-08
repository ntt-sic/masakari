import uuid
import time
import datetime
from sqlalchemy.orm import sessionmaker
import sys
from sqlalchemy import create_engine
from models import Base
from models import NotificationList, VmList, ReserveList
from sqlalchemy.orm import scoped_session
import api as dbapi
import random


class sqlalchemyTest(object):

    def __init__(self):
        try:
            self.engine = create_engine('sqlite:///:memory:', echo=False)
            # Create all tables in the engine
            Base.metadata.create_all(self.engine)
            session_factory = sessionmaker(bind=self.engine)
            self.Session = scoped_session(session_factory)
        except Exception as e:
            # error handling
            print "failed to create tables."
            print "Exception: ", e
            sys.exit(2)

    def addtoVmList(self, create_at, deleted, uuid, progress,
                    retry_cnt, notification_id, recover_to, recover_by):

        vm_list = VmList(create_at=create_at, deleted=deleted, uuid=uuid,
                         progress=progress, retry_cnt=retry_cnt,
                         notification_id=notification_id,
                         recover_to=recover_to,
                         recover_by=recover_by)
        self.Session.add(vm_list)
        return vm_list

    def addtoReserveList(self, create_at, deleted,
                         cluster_port, hostname):
        reslist = ReserveList(
            create_at=create_at,
            deleted=deleted,
            cluster_port=cluster_port,
            hostname=hostname)
        self.Session.add(reslist)
        return reslist

    def addtoNotificationList(self, **kwargs):
        # Thing generate for each event
        t = datetime.datetime.now()
        currentTime = t.strftime('%Y%m%d%H%M%S')
        tz_name = time.tzname
        tz_name_str = str(tz_name)
        tz_name_str = tz_name_str.lstrip('(')
        tz_name_str = tz_name_str.rstrip(')')
        time_daylight = time.daylight
        time_daylight_str = str(time_daylight)
        notification_list = NotificationList(
            create_at=kwargs.pop('create_at', t),
            update_at=kwargs.pop('update_at', t),
            delete_at=kwargs.pop('delete_at', t),
            deleted=kwargs.pop('deleted', 0),
            notification_id=kwargs.pop('notification_id', str(uuid.uuid4())),
            notification_type=kwargs.pop('notification_type', "1"),
            notification_regionID=kwargs.pop('notification_regionID',
                                             "RegionOne"),
            notification_hostname=kwargs.pop(
                'notification_hostname', "compute01"),
            notification_uuid=kwargs.pop(
                'notification_uuid', None),
            notification_time=kwargs.pop(
                'notification_time', t),
            notification_eventID=kwargs.pop('notification_eventID', "1"),
            notification_eventType=kwargs.pop('notification_eventType', "VM"),
            notification_detail=kwargs.pop('notification_detail', "1"),
            notification_startTime=kwargs.pop(
                'notification_startTime', t),
            notification_endTime=kwargs.pop(
                'notification_endTime', t),
            notification_tzname=kwargs.pop('notification_tzname', tz_name_str),
            notification_daylight=kwargs.pop('notification_daylight',
                                             time_daylight_str),
            notification_cluster_port=kwargs.pop('notification_cluster_port',
                                                 None),
            progress=kwargs.pop('progress', "0"),

            recover_by=kwargs.pop('recover_by', None),
            iscsi_ip=kwargs.pop('iscsi_ip', None),
            controle_ip=kwargs.pop('controle_ip', "192.168.50.10"),
            recover_to=kwargs.pop('recover_to', "compute01")
        )
        self.Session.add(notification_list)
        self.Session.commit()
        return notification_list

    def testcaseH(self):
        # result = {}
        self.addtoNotificationList(noticeType='VM',
                                   uuid=None, eventType=1,
                                   eventID=2, detail=2)
        q = self.Session.query(NotificationList).filter_by(progress="0").all()
        for i in q:
            print i.notification_id

    def test_get_old_records_notification(self):
        now = datetime.datetime.now()
        notification_expiration_sec = int(360)
        dummy_created_at = now - datetime.timedelta(
            seconds=notification_expiration_sec)
        # Create few dummy expired records
        for i in xrange(10):
            self.addtoNotificationList(create_at=dummy_created_at,)
        # Add few new records
        for i in xrange(10):
            self.addtoNotificationList(create_at=datetime.datetime.now())
        now = datetime.datetime.now()
        notification_expiration_sec = int(120)
        border_time = now - datetime.timedelta(
            seconds=notification_expiration_sec)
        print type(border_time)
        border_time_str = border_time.strftime('%Y-%m-%d %H:%M:%S')
        print type(border_time_str)
        res = dbapi.get_old_records_notification(self.Session, border_time_str)
        for row in res:
            print row.id

    def test_delet_expired_notification(self):
        now = datetime.datetime.now()
        notification_expiration_sec = int(360)
        dummy_created_at = now - datetime.timedelta(
            seconds=notification_expiration_sec)
        # Create few dummy expired records
        for i in xrange(10):
            self.addtoNotificationList(create_at=dummy_created_at)
        # Add few new records
        for i in xrange(10):
            self.addtoNotificationList(create_at=datetime.datetime.now())
        now = datetime.datetime.now()
        notification_expiration_sec = int(120)
        border_time = now - datetime.timedelta(
            seconds=notification_expiration_sec)
        border_time_str = border_time.strftime('%Y-%m-%d %H:%M:%S')
        res = dbapi.get_old_records_notification(self.Session, border_time_str)
        for row in res:
            res = dbapi.delet_expired_notification(self.Session, 4,
                                                   datetime.datetime.now(),
                                                   datetime.datetime.now(),
                                                   row.id)
            print res

    def test_get_reprocessing_records_list_distinct(self):
        for i in xrange(3):
            # generate 3 records with same uuid
            fix_uuid = str(uuid.uuid4())
            for j in xrange(10):
                self.addtoNotificationList(progress=0,
                                           recover_by=1,
                                           notification_uuid=fix_uuid)
        # Get them throug api
        result = dbapi.get_reprocessing_records_list_distinct(self.Session)
        for row in result:
            print row.notification_uuid

    def test_get_notification_list_distinct_hostname(self):
        for i in xrange(3):
            # generate 3 records with same uuid
            fix_uuid = str(uuid.uuid4())
            for j in xrange(10):
                self.addtoNotificationList(progress=0,
                                           recover_by=0,
                                           notification_uuid=fix_uuid)
        # Get them throug api
        result = dbapi.get_notification_list_distinct_hostname(self.Session)
        for row in result:
            print row.notification_hostname

    def test_get_reprocessing_records_list(self):
        query_list = []
        for i in xrange(3):
            # generate 3 records with same uuid
            fix_uuid = str(uuid.uuid4())
            query_sub_list = []
            for j in xrange(10):
                if j % 2 == 0:
                    # create 2 rows with same time stamp with different ids
                    now = datetime.datetime.now()
                    diff = random.randint(1, 100)
                    create_at = now - datetime.timedelta(seconds=diff)
                col = self.addtoNotificationList(progress=0,
                                                 recover_by=1,
                                                 notification_uuid=fix_uuid,
                                                 create_at=create_at)
                query_sub_list.append(col)
            # Sort the query_sub_list with create_at, and then id
            query_sub_list = sorted(query_sub_list,
                                    key=lambda x: (x.create_at, x.id),
                                    reverse=True)
            query_list.append(query_sub_list)

        # Get them through api
        # get the uuid list
        result = dbapi.get_reprocessing_records_list_distinct(self.Session)
        # get the records from above uuid
        for row in result:
            result2 = dbapi.get_reprocessing_records_list(
                self.Session, row.notification_uuid)
            for record in query_list:
                # Dont use Python Identity Operators such as 'if # is #:'
                # Identity operators compare memory locations of two objects.
                # Use '==' to compare values
                if record[0].notification_uuid == row.notification_uuid:
                    break

            rindex = 0
            # Check the records are correct order as we put them
            for row2 in result2:
                if row2 is record[rindex]:
                    print "OK"
                else:
                    print "ERROR"
                rindex += 1

    def test_get_notification_list_by_hostname(self):
        query_list = []
        for i in xrange(10):
            hostname = "compute02"
            if i % 2 == 0:
                # create 2 rows with same time stamp with different ids
                now = datetime.datetime.now()
                diff = random.randint(1, 100)
                create_at = now - datetime.timedelta(seconds=diff)
            col = self.addtoNotificationList(
                progress=0,
                notification_hostname=hostname,
                create_at=create_at)
            query_list.append(col)
            # Sort the query_sub_list with create_at, and then id
            query_list = sorted(query_list,
                                key=lambda x: (x.create_at, x.id),
                                reverse=True)
        result = dbapi.get_notification_list_by_hostname(
            self.Session, hostname)
        for r in result:
            if r is query_list.pop(0):
                print "OK"
            else:
                print "ERROR"

    def test_update_reprocessing_records(self):
        # add a dummy records
        fix_uuid = str(uuid.uuid4())
        rec = self.addtoNotificationList(create_at=datetime.datetime.now(),
                                         notification_uuid=fix_uuid)
        id = rec.id
        update_at = datetime.datetime.now()
        delete_at = datetime.datetime.now()
        dbapi.update_reprocessing_records(
            self.Session, 4, update_at, delete_at, id)
        row = self.Session.query(NotificationList).filter_by(
            notification_uuid=fix_uuid)
        for r in row:
            print r.progress

    def test_get_all_notification_list_by_notification_id(self):
        fix_uuid = str(uuid.uuid4())
        for i in xrange(10):
            if i == 0:
                var_uuid = fix_uuid
            else:
                var_uuid = str(uuid.uuid4())
            self.addtoNotificationList(notification_id=var_uuid)
        res = dbapi.get_all_notification_list_by_notification_id(
            self.Session, fix_uuid)
        for r in res:
            if r.notification_id == fix_uuid:
                print "OK"
            else:
                print "ERROR"

    def test_get_all_notification_list_by_hostname_with_rscgroup_type(self):
        # Test with empty db
        # Nothing shold come out
        res = dbapi.get_all_notification_list_by_hostname_with_rscgroup_type(
            self.Session,
            "compute02"
        )

        def check_empty(obj):
            print obj
            if not obj:
                print "EMPTY"
            else:
                print "NOT EMPTY"
        check_empty(res)
        # put some records and test
        # Records older than 25s should not count
        # This value (25s) is experimental
        for i in xrange(10):
            now = datetime.datetime.now()
            diff = random.randint(50, 100)
            nt = now - datetime.timedelta(seconds=diff)
            self.addtoNotificationList(
                notification_hostname="compute02",
                notification_time=nt,
                notification_type="rscGroup")
        notification_time = datetime.datetime.now()
        res = dbapi.get_all_notification_list_by_hostname_with_rscgroup_type(
            self.Session,
            "compute02"
        )
        check_empty(res)
        flg = 0
        for row in res:
            db_time = row.notification_time
            delta = notification_time - db_time
            if long(delta.total_seconds()) <= long(25):
                flg = 1
        if flg == 0:
            print "OK"


def run_test():
    test = sqlalchemyTest()
    # test.test_get_old_records_notification()
    # test.test_delet_expired_notification()
    # test.test_get_reprocessing_records_list_distinct()
    # test.test_get_reprocessing_records_list()
    # test.test_update_reprocessing_records()
    # test.test_get_notification_list_distinct_hostname()
    # test.test_get_notification_list_by_hostname()
    # test.test_get_all_notification_list_by_notification_id()
    test.test_get_all_notification_list_by_hostname_with_rscgroup_type()
if __name__ == '__main__':
    run_test()
