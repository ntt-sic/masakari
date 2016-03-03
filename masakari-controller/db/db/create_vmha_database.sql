create database vm_ha;
use vm_ha;
create table notification_list
(
id int AUTO_INCREMENT primary key,
create_at datetime ,
update_at datetime ,
delete_at datetime ,
deleted int ,
notification_id varchar(256),
notification_type varchar( 16),
notification_regionID varchar( 256),
notification_hostname varchar( 256),
notification_uuid varchar( 256),
notification_time datetime ,
notification_eventID varchar( 1),
notification_eventType varchar( 1),
notification_detail varchar( 2),
notification_startTime datetime ,
notification_endTime datetime ,
notification_tzname varchar( 16),
notification_daylight varchar( 1),
notification_cluster_port varchar( 64),
progress int ,
recover_by int ,
iscsi_ip varchar( 16),
controle_ip varchar( 16),
recover_to varchar( 256)
);

desc notification_list;

create table vm_list
(
id int  AUTO_INCREMENT primary key,
create_at datetime ,
update_at datetime ,
delete_at datetime ,
deleted int ,
uuid varchar( 64),
progress int ,
retry_cnt int ,
notification_id varchar( 256),
recover_to varchar( 256),
recover_by int
);

desc vm_list;



create table reserve_list
(
id int  AUTO_INCREMENT primary key,
create_at datetime ,
update_at datetime ,
delete_at datetime ,
deleted int ,
cluster_port varchar( 64),
hostname  varchar( 256)
);

desc reserve_list;

