drop table if exists hn_dev.post_score;
create table hn_dev.post_score
(
	post_uuid varchar(255) not null,
	role_group_id int not null,
	score int not null,
	calendar_id text not null,
	post_id int not null,
	constraint post_score_pk
		primary key (role_group_id, post_uuid)
);

drop table if exists post_details;
create table post_details
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


drop table if exists hn_dev.role_groups;
create table hn_dev.role_groups
(
	role_group_id int not null,
	role_group_name text not null,
	buzz_words longtext not null,
	constraint role_groups_pk
		primary key (role_group_id)
);


INSERT INTO `hn_dev`.`role_groups` (`role_group_id`, `role_group_name`, `buzz_words`) VALUES (1, 'Data_Science', '''machine learning'', ''data science'', ''data analytics'', ''data engineering'', ''big data'', ''python'', ''ai'', ''artificial intelligence'', ''neural networks'', ''deep learning'', ''data scientist'', ''computer vision'', ''ml'', ''machine-learning'', ''natural language'', ''nlp'', ''sentiment analysis''');
INSERT INTO `hn_dev`.`role_groups` (`role_group_id`, `role_group_name`, `buzz_words`) VALUES (2, 'Front_End', '''nodejs'', ''react'', ''angular'', ''html'', ''css'', ''aws'', ''ci/cd''');
INSERT INTO `hn_dev`.`role_groups` (`role_group_id`, `role_group_name`, `buzz_words`) VALUES (3, 'DevOps', '''terraform'', ''aws'', ''aws'', ''heroku'', ''kubernetes'', ''deployment'', ''circleci'', ''ansible''');

drop table if exists post_raw;
create table post_raw
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


drop table if exists hn_dev.calendar_thread;
create table hn_dev.calendar_thread
(
	month varchar(8) not null,
	parent_id int not null,
    ingested_post_id int not null,
	constraint calendar_thread_pk
		primary key (month)
);



INSERT INTO `hn_dev`.`calendar_thread` (`month`, `parent_id`, `ingested_post_id`) VALUES ('oct_2019', 21126014, 0);
INSERT INTO `hn_dev`.`calendar_thread` (`month`, `parent_id`, `ingested_post_id`) VALUES ('aug_2019', 20584311, 0);
