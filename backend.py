import pymysql
import boto3
import sys
from config import config
from flask import Flask, request

ssm_client = boto3.client('ssm', region_name=config['aws_region'])
parameters = ssm_client.get_parameters_by_path(
    Path='/dev/rds',
    Recursive=True)

if 'Parameters' in parameters and len(parameters.get('Parameters')) > 0:
    params = parameters.get('Parameters')
    for param in params:
        param_path_array = param.get('Name').split("/")
        section_name = param_path_array[-1]
        config_values = param.get('Value')
        config[section_name] = config_values

try:
    conn = pymysql.connect(host=config['host'], user=config['name'], passwd=config['password'],
                           db=config['db_name'], port=int(config['port']), connect_timeout=5)
except Exception as e:
    print(e)
    sys.exit()


dynamodb_client = boto3.resource('dynamodb', region_name=config['aws_region'])
user_role_group_id_table = dynamodb_client.Table('user_role_group_id')
user_processed_post_table = dynamodb_client.Table('user_processed_posts')
user_stage_table = dynamodb_client.Table('Post_Stage')


app = Flask(__name__)


@app.route('/role_groups', methods=['GET'])
def list_role_groups():
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute('select * from hn_dev.role_groups')
    res = cur.fetchall()
    return {'role_groups': res}


@app.route('/users/<user_id>/rolegroupid', methods=['GET', 'POST'])
def update_user_rolegroupid(user_id):
    if request.method == 'GET':
        response = user_role_group_id_table.get_item(
            Key={
                'user_id': user_id
            }
        )
        if 'Item' not in response:
            return {'user_id': user_id, 'role_group_id': None}
        else:
            return response['Item']
    else:
        role_group_id = request.form['role_group_id']
        user_role_group_id_table.put_item(
            Item={
                'user_id': user_id,
                'role_group_id': role_group_id
            }
        )
        return {'user_id': user_id, 'role_group_id': role_group_id}


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)
