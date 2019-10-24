import pymysql
import sys
import os
from typing import List
from utils import get_ssm_dict
import boto3
from boto3.dynamodb.table import TableResource


rds_config = get_ssm_dict('/{env}/rds'.format(env=os.environ.get('ENV', 'test')))
dynamodb_config = get_ssm_dict('/{env}/dynamodb'.format(env=os.environ.get('ENV', 'test')))


def get_connection():
    try:
        connection = pymysql.connect(host=rds_config['host'], user=rds_config['name'], passwd=rds_config['password'],
                                     db=rds_config['db_name'], port=int(rds_config['port']), connect_timeout=5)
    except Exception as e:
        print(e)
        sys.exit()
    return connection


conn = get_connection()
dynamodb_client = boto3.resource('dynamodb', region_name='us-east-1')
user_role_group_id_table = dynamodb_client.Table(dynamodb_config['user_rolegroupid'])
user_processed_post_table = dynamodb_client.Table(dynamodb_config['user_latest_posts'])
user_stage_table = dynamodb_client.Table(dynamodb_config['user_post_stage'])


def insert_items(table: TableResource, items: List[dict]):
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(
                Item=item
            )


def setup_get_post_ids_in_view():
    user_id = 'non_empty_user_postidview'
    calendar_id = 'test_2019'
    stage_id = 99
    calendar_stage_uuid = '|'.join([calendar_id, str(stage_id)])
    post_ids = [x for x in range(1, 5)]
    items = [{'user_id': user_id, 'post_id': str(x), 'calendar_stage_uuid': calendar_stage_uuid} for x in post_ids]
    insert_items(user_stage_table, items)


def setup_get_view():
    user_id = 'non_empty_view_user'
    calendar_id = 'test_2019'
    stage_id = 99
    calendar_stage_uuid = '|'.join([calendar_id, str(stage_id)])
    post_ids = [1, 2, 4, 6]
    items = [{'user_id': user_id, 'post_id': str(x), 'calendar_stage_uuid': calendar_stage_uuid} for x in post_ids]
    insert_items(user_stage_table, items)

    rolegroup = [{'user_id': user_id, 'role_group_id': 1}]
    insert_items(user_role_group_id_table, rolegroup)


if __name__ == '__main__':
    setup_get_post_ids_in_view()
    setup_get_view()
