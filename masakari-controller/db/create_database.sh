#!/bin/sh
#
#

source db.conf

mysql -u${DB_USER} -p${DB_PASSWORD} -h${DB_HOST} -e "drop database vm_ha"
mysql -u${DB_USER} -p${DB_PASSWORD} -h${DB_HOST} -e "source create_vmha_database.sql"
