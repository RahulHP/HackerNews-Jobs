drop table if exists hn_jobs_test.post_score;
create table hn_jobs_test.post_score
(
	post_uuid varchar(255) not null,
	role_group_id int not null,
	score int not null,
	calendar_id text not null,
	post_id int not null,
	constraint post_score_pk
		primary key (role_group_id, post_uuid)
);

drop table if exists hn_jobs_test.post_details;
create table hn_jobs_test.post_details
(
	post_uuid varchar(255) not null,
	role text null,
	company text null,
	post_text longtext not null,
	poster_id text not null,
	post_time int not null,
	parent_id int not null,
	calendar_id text not null,
	post_id int not null,
	constraint post_details_pk
		primary key (post_uuid)
);


drop table if exists hn_jobs_test.role_groups;
create table hn_jobs_test.role_groups
(
	role_group_id int not null,
	role_group_name text not null,
	buzz_words longtext not null,
	constraint role_groups_pk
		primary key (role_group_id)
);


drop table if exists hn_jobs_test.post_raw;
create table hn_jobs_test.post_raw
(
	id int not null,
	parent int null,
	`by` text null,
	time int null,
	text longtext null,
	calendar text not null,
	constraint post_raw_pk
		primary key (id)
);


drop table if exists hn_jobs_test.calendar_thread;
create table hn_jobs_test.calendar_thread
(
  month_id int not null,
	month varchar(8) not null,
	parent_id int not null,
    ingested_post_id int not null,
	constraint calendar_thread_pk
		primary key (month)
);
