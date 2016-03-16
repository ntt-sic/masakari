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

import sys
import os
parentdir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                         os.path.pardir))
sys.path = [parentdir] + sys.path

from sqlalchemy import create_engine
from sqlalchemy_utils.functions import database_exists, create_database
from controller.masakari_config import RecoveryControllerConfig
from db.models import Base
from db import api as dbapi


# Todo(sampath): No need this file
# call dbapi.create_tables() to create tables

try:
    # retrieve configuration parameters
    config = RecoveryControllerConfig()
    conf_db_dic = config.get_value('db')
    host = conf_db_dic.get("host")
    db = conf_db_dic.get("name")
    user = conf_db_dic.get("user")
    passwd = conf_db_dic.get("passwd")
    charset = conf_db_dic.get("charset")
except Exception as e:
    # error handling
    print "failed to load configuration parameters."
    print "Exception: ", e
    sys.exit(1)

print "host:", host, "db:", db, "user:", user, "passwd:", passwd, "charset:", charset

try:
    # Create an engine to store data in the database
    engine = dbapi.get_engine()
    # Create database if not exists
    if not database_exists(engine.url):
        create_database(engine.url)
    # Create all tables in the engine
    Base.metadata.create_all(engine)
except Exception as e:
    # error handling
    print "failed to create tables."
    print "Exception: ", e
    sys.exit(2)

print "Successfully created tables"
sys.exit(0)
