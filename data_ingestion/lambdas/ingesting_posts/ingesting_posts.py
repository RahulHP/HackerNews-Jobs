import requests
import boto3
import pymysql
import os

client = boto3.client('ssm')
parameters = client.get_parameters_by_path(
    Path='/rds'.format(env=os.environ['env']),
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

API_BASE_URL = 'https://hacker-news.firebaseio.com/v0/item/'


def get_job_details(job_id, month):
    job_link = API_BASE_URL + str(job_id) + '.json'
    data = requests.get(job_link).json()
    return data['id'], data['parent'], data.get('by', 'None'), data['time'], data.get('text', 'None'), month


def get_thread(month):
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute('SELECT * from calendar_thread WHERE month = "{month}"'.format(month=month))
        res = cur.fetchone()
    return res['parent_id'], res['ingested_post_id']


def update_thread(month, new_value):
    with conn.cursor() as cur:
        cur.execute('UPDATE calendar_thread SET ingested_post_id = {new_value} WHERE month = "{month}"'.format(
            new_value=new_value, month=month))
    conn.commit()


def lambda_handler(event, context):
    parent_id, max_post = get_thread(event['calendar_id'])

    url = 'https://hacker-news.firebaseio.com/v0/item/{thread_id}.json'.format(thread_id=parent_id)
    data = requests.get(url).json()
    jobs = data['kids']
    job_details = list()

    print("Getting children data")
    # print(data)
    for i in jobs:
        if i > max_post:
            job_details.append(get_job_details(str(i), event['calendar_id']))
    print("Inserting SQL")
    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO post_raw (id, parent, `by`, time, text, calendar)
            VALUES (%s, %s, %s, %s, %s, %s)""", job_details)
        conn.commit()
    new_max_value = max(jobs)
    update_thread(event['calendar_id'], new_max_value)

    # TODO implement
    return {
        'calendar_id': event['calendar_id']
    }
