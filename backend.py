import pymysql
import boto3
import sys
import os
from functools import wraps
from utils import get_ssm_dict
from flask import Flask, request, url_for
from boto3.dynamodb.conditions import Key, Attr
import requests


rds_config = get_ssm_dict('/rds')
dynamodb_config = get_ssm_dict('/{env}/dynamodb'.format(env=os.environ['ENV']))

if os.environ['DATA_ENV'].lower() == 'live':
    db_name = rds_config['db_name']
else:
    db_name = '{db}_{env}'.format(db=rds_config['db_name'], env=os.environ['DATA_ENV'].lower())

def get_connection():
    try:
        conn = pymysql.connect(host=rds_config['host'], user=rds_config['name'], passwd=rds_config['password'],
                               db=db_name, port=int(rds_config['port']), connect_timeout=5)
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
        cur.execute('select * from role_groups')
    res = cur.fetchall()
    return {'role_groups': res}


@app.route('/calendar', methods=['GET'])
@rds_conn_required
def list_months():
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        query = """
        select month from calendar_thread
        order by month_id desc;
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
    results_list = [int(i['post_id']) for i in items]
    results_list.sort()
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
    update_post_stage(user_id, post_id, calendar_id, stage_id)
    return {'code': 200}


@app.route('/users/<user_id>/calendar/<calendar_id>/stage/<stage_id>/view', methods=['GET'])
def get_view(user_id, calendar_id, stage_id):
    post_ids = get_post_ids_in_view(user_id, calendar_id, stage_id)['results']
    user_role_group_id = get_user_rolegroupid(user_id)['role_group_id']
    post_details = get_post_details(calendar_id, post_ids, user_role_group_id)
    return {'results': post_details}


@app.route('/users/<user_id>/batch_posts', methods=['POST'])
def api_batch_create_records(user_id):
    calendar_id = request.form.get('calendar_id')
    stage_id = request.form.get('stage_id')
    posts = request.form.getlist('post_id_batch')
    batch_create_records(user_id, calendar_id, posts, stage_id)
    return {'code': 200}

def batch_create_records(user_id, calendar_id, post_ids, stage=0):
    calendar_stage_uuid = '|'.join([calendar_id,str(stage)])
    with user_stage_table.batch_writer() as batch:
        for post_id in post_ids:
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
        new_last_processed_post = max(new_posts)
        set_last_processed_post(user_id, calendar_id, new_last_processed_post)
        print('LAST PROCESSED POST:', new_last_processed_post)
        return {'last_processed_post': new_last_processed_post}
    else:
        return {'last_processed_post': last_processed_post}


@app.route('/users/<user_id>/calendar/<calendar_id>/latest_post', methods=['GET', 'POST'])
def api_latest_post(user_id, calendar_id):
    if request.method == 'GET':
        return get_last_processed_post(user_id, calendar_id)
    else:
        post_id = request.form['latest_post']
        set_last_processed_post(user_id, calendar_id, post_id)
        return {'last_processed_post': int(post_id)}


def set_last_processed_post(user_id, calendar_id, last_post):
    user_processed_post_table.update_item(
        Key={'user_id': user_id,
             'calendar_id': calendar_id},
        UpdateExpression='SET post_id = :post',
        ExpressionAttributeValues={
            ':post': int(last_post)
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


@app.route('/calendar/<calendar_id>/new_posts', methods=['GET'])
def api_get_new_posts(calendar_id):
    last_post = request.args.get('last_post')
    new_posts = get_newer_posts(calendar_id, last_post)
    return {'new_posts': new_posts}


@rds_conn_required
def get_newer_posts(calendar_id, last_post):
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        query = """
        select post_id from post_details where calendar_id="{calendar}" and post_id > {post}
        order by post_id desc
        """.format(calendar=calendar_id, post=last_post)
        cur.execute(query)
    res = cur.fetchall()
    results = [x['post_id'] for x in res]
    return results


@rds_conn_required
def get_post_details(calendar_id, post_ids, role_group_id):
    if len(post_ids)==0:
        return [None]
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        query = """
        select details.post_id, post_text, post_time, poster_id, score from
            (select * from post_details where calendar_id='{cal_id}') details
            inner join
            (select * from post_score where calendar_id='{cal_id}' and role_group_id={rg_id}) scores
            on details.post_uuid = scores.post_uuid
            where scores.post_id in ({post_list})
            order by score desc, details.post_id desc;
        """.format(cal_id=calendar_id, rg_id=role_group_id, post_list=','.join(str(x) for x in post_ids))
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
        return {'user_id': user_id, 'role_group_id': int(response['Item']['role_group_id'])}


def update_user_rolegroupid(user_id, role_group_id):
    user_role_group_id_table.put_item(
        Item={
            'user_id': user_id,
            'role_group_id': int(role_group_id)
        }
    )


@app.route('/users/<user_id>/rolegroupid', methods=['GET', 'POST'])
def api_user_rolegroupid(user_id):
    if request.method == 'GET':
        return get_user_rolegroupid(user_id)
    else:
        role_group_id = request.form['role_group_id']
        update_user_rolegroupid(user_id, role_group_id)
        return {'user_id': user_id, 'role_group_id': int(role_group_id)}


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)
