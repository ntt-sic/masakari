# How to setup

## Before run masakari-controller
1. DB setup

   Masakari controller need access to db. If you have pre-configured db, then skip this step.

   Install mysql-server and setup.

   Ubuntu:
	sudo apt-get install mysql-server

	Centos 6 or before:
	(not tested)
	sudo yum install mysql-server

   Centos 7:

   	Use MariaDB instead of MySQL. MariaDb is a open source equivalent to MySQL and can be installed with

	```sh
	#yum -y install mariadb-server mariadb
	```

	Then,

	```sh
	#mysql_secure_installation
	```
	to configure it.

	If you need mysql, then add the mysql-community repo by,

	```sh
	#rpm -Uvh http://dev.mysql.com/get/mysql-community-release-el7-5.noarch.rpm
	```

	Or,

	```sh
	#wget http://repo.mysql.com/mysql-community-release-el7-5.noarch.rpm
	#rpm -ivh mysql-community-release-el7-5.noarch.rpm
	#yum update
	```
	and then you can install MySQLl like you normally do.

	```sh
	#yum install mysql-server
	#systemctl start mysqld
	```

2. Install basic requirements
   Install the basic python requirements,
   Ubuntu:

   ```sh
   #apt-get install python-setuptools python-devel
   ```

   CentOS:

   ```sh
   #yum install python-setuptools python-devel
   ```

   Install mysql-devel before install MySQLdb
   Ubuntu:

   ```sh
   #apt-get install mysql-devel
   ```

   CentOS:

   ```sh
   #yum -y install  mysql-devel
   ```

   Ubuntu:

   ```sh
   #apt-get install build-essential
   ```

   CentOS:

   ```sh
   #yum groupinstall "Development tools"
   ```

   or

   ```sh
   #yum groupinstall -y development
   ```

3. Create db and tables

   All the tools you need to create the db and tables are in,
   masakari/masakari-controller/db/
   cd to dir,

   ```sh
   $cd masakari/masakari-controller/db/
   ```

   First, configure the db.conf

   ~~~
      DB_USER=[db user name]
      DB_PASSWORD=[pwd for the user]
      DB_HOST=[fqdn or ip for the db server]
   ~~~

   Then, this will create the db and required tables for masakari-controller

   ```sh
   $./create_database.sh
   ```
4. Setup

   Go to masakari/masakari-controller and,

   ```sh
   $sudo pip install -e .
   ```
   Executable place in /usr/bin/masakari-controller

   > If no pip,
   >
   > curl -O https://bootstrap.pypa.io/get-pip.py
   >
   > sudo python get-pip.py
   >
   > sudo yum -y install python-devel
