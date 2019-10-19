import pymysql
import boto3
import sys
import os
from functools import wraps
from utils import get_ssm_dict
from flask import Flask, request, url_for
from boto3.dynamodb.conditions import Key, Attr
import requests


rds_config = get_ssm_dict('/{env}/rds'.format(env=os.environ.get('ENV', 'dev')))
dynamodb_config = get_ssm_dict('/{env}/dynamodb'.format(env=os.environ.get('ENV', 'dev')))

def get_connection():
    try:
        conn = pymysql.connect(host=rds_config['host'], user=rds_config['name'], passwd=rds_config['password'],
                               db=rds_config['db_name'], port=int(rds_config['port']), connect_timeout=5)
    except Exception as e:
        print(e)
        sys.exit()
    return conn


conn = get_connection()
dynamodb_client = boto3.resource('dynamodb', region_name='us-east-1')
user_role_group_id_table = dynamodb_client.Table(dynamodb_config['user_rolegroupid'])
user_processed_post_table = dynamodb_client.Table(dynamodb_config['user_latest_posts'])
user_stage_table = dynamodb_client.Table(dynamodb_config['user_post_stage'])


app = Flask(__name__)


def rds_conn_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        conn.ping(reconnect=True)
        return f(*args, **kwargs)
    return wrap


@app.route('/role_groups', methods=['GET'])
@rds_conn_required
def list_role_groups():
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute('select * from hn_jobs.role_groups')
    res = cur.fetchall()
    return {'role_groups': res}


@app.route('/calendar', methods=['GET'])
@rds_conn_required
def list_months():
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        query = """
        select month from hn_jobs.calendar_thread
        """
        cur.execute(query)
        results = cur.fetchall()
    return {'results':results}


@app.route('/users/<user_id>/calendar/<calendar_id>/stage/<stage_id>/post_ids')
def get_post_ids_in_view(user_id, calendar_id, stage_id):
    calendar_stage_uuid ='|'.join([calendar_id, stage_id])
    response = user_stage_table.query(
        IndexName='user_calendar_stage',
        KeyConditionExpression=Key('user_id').eq(str(user_id)) & Key('calendar_stage_uuid').eq(calendar_stage_uuid)
    )
    items = response['Items']
    results_list = [i['post_id'] for i in items]
    results = {'results': results_list}
    return results


def update_post_stage(user_id, post_id, calendar_id, stage_id):
    user_stage_table.update_item(
        Key={'user_id': user_id,
             'post_id': post_id},
        UpdateExpression='SET calendar_stage_uuid = :cal_stage',
        ExpressionAttributeValues={
            ':cal_stage': '|'.join([calendar_id, stage_id])
        }
    )


@app.route('/users/<user_id>/posts', methods=['POST'])
def update_post(user_id):
    calendar_id = request.form.get('calendar_id')
    stage_id = request.form.get('stage_id')
    post_id = request.form.get('post_id')
    print(user_id,post_id,calendar_id,stage_id)
    update_post_stage(user_id, post_id, calendar_id, stage_id)
    return {'code': 200}


@app.route('/users/<user_id>/calendar/<calendar_id>/stage/<stage_id>/view')
def get_view(user_id, calendar_id, stage_id):
    post_ids = get_post_ids_in_view(user_id, calendar_id, stage_id)['results']
    user_role_group_id = get_user_rolegroupid(user_id)['role_group_id']
    post_details = get_post_details(calendar_id, post_ids, user_role_group_id)
    return {'results': post_details}


def batch_create_records(user_id, calendar_id, post_ids, stage=0):
    calendar_stage_uuid = '|'.join([calendar_id,str(stage)])
    with user_stage_table.batch_writer() as batch:
        for post in post_ids:
            post_id = post['post_id']
            batch.put_item(
                Item={
                    'user_id': str(user_id),
                    'post_id': str(post_id),
                    'calendar_stage_uuid': calendar_stage_uuid
                }
            )


@app.route('/users/<user_id>/calendar/<calendar_id>/update_posts', methods=['POST'])
def create_records_for_new_posts(user_id, calendar_id):
    last_processed_post = get_last_processed_post(user_id, calendar_id)['last_processed_post']
    print('LAST PROCESSED POST:', last_processed_post)
    new_posts = get_newer_posts(calendar_id, last_processed_post)
    if len(new_posts) != 0:
        print("UPDATING POSTS", len(new_posts))
        batch_create_records(user_id, calendar_id, new_posts)
        new_last_processed_post = max(i['post_id'] for i in new_posts)
        set_last_processed_post(user_id, calendar_id, new_last_processed_post)
        print('LAST PROCESSED POST:', new_last_processed_post)
    return {'last_processed_post': new_last_processed_post}


def set_last_processed_post(user_id, calendar_id, last_post):
    user_processed_post_table.update_item(
        Key={'user_id': user_id,
             'calendar_id': calendar_id},
        UpdateExpression='SET post_id = :post',
        ExpressionAttributeValues={
            ':post': last_post
        }
    )


def get_last_processed_post(user_id, calendar_id):
    ans = user_processed_post_table.get_item(
        Key={
            'user_id': user_id,
            'calendar_id': calendar_id
        }
    )
    if 'Item' in ans:
        return {'last_processed_post': int(ans['Item']['post_id'])}
    else:
        user_processed_post_table.put_item(
            Item={
                'user_id':user_id,
                'calendar_id': calendar_id,
                'post_id': 0
            }
        )
        return {'last_processed_post': 0}


@rds_conn_required
def get_newer_posts(calendar_id, last_post):
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        query = """
        select post_id from hn_jobs.post_details where calendar_id="{calendar}" and post_id >= {post}
        """.format(calendar=calendar_id, post=last_post)
        print(query)
        cur.execute(query)
    res = cur.fetchall()
    return res


@rds_conn_required
def get_post_details(calendar_id, post_ids, role_group_id):
    if len(post_ids)==0:
        return [None]
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        query = """
        select * from
            (select * from hn_jobs.post_details where calendar_id='{cal_id}') details
            inner join
            (select * from hn_jobs.post_score where calendar_id='{cal_id}' and role_group_id={rg_id}) scores
            on details.post_uuid = scores.post_uuid
            where scores.post_id in ({post_list})
            order by score desc;
        """.format(cal_id=calendar_id, rg_id=role_group_id, post_list=','.join(post_ids))
        print(query)
        cur.execute(query)
        results = cur.fetchall()
    return results


def get_user_rolegroupid(user_id):
    response = user_role_group_id_table.get_item(
        Key={
            'user_id': user_id
        }
    )
    if 'Item' not in response:
        return {'user_id': user_id, 'role_group_id': None}
    else:
        return response['Item']


def update_user_rolegroupid(user_id, role_group_id):
    user_role_group_id_table.put_item(
        Item={
            'user_id': user_id,
            'role_group_id': role_group_id
        }
    )


@app.route('/users/<user_id>/rolegroupid', methods=['GET', 'POST'])
def api_user_rolegroupid(user_id):
    if request.method == 'GET':
        return get_user_rolegroupid(user_id)
    else:
        role_group_id = request.form['role_group_id']
        update_user_rolegroupid(user_id, role_group_id)
        return {'user_id': user_id, 'role_group_id': role_group_id}


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)
