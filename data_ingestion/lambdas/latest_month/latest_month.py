import pymysql
import os
import boto3

client = boto3.client('ssm')
parameters = client.get_parameters_by_path(
    Path='/{env}/rds'.format(env=os.environ['env']),
    Recursive=True)

config = dict()

if 'Parameters' in parameters and len(parameters.get('Parameters')) > 0:
    params = parameters.get('Parameters')
    for param in params:
        param_path_array = param.get('Name').split("/")
        section_name = param_path_array[-1]
        config_values = param.get('Value')
        config[section_name] = config_values

conn = pymysql.connect(host=config['host'], user=config['name'], passwd=config['password'], db=config['db_name'],
                       port=int(config['port']), connect_timeout=5)


def get_latest_month():
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute('select month from hn_jobs.calendar_thread order by month_id desc limit 1')
        res = cur.fetchone()
    return res['month']


def lambda_handler(event, context):
    month = get_latest_month()
    return {
        'calendar_id': month
    }
