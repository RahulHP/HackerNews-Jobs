import json
import boto3
import pymysql
import ast

client = boto3.client('ssm')
parameters = client.get_parameters_by_path(
    Path='/dev/rds',
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


def get_score(text, buzz):
    if text is None:
        return -99
    text = text.lower()
    score = 0
    for w in buzz:
        if w in text:
            score += 1
    return score


def score_and_insert(calendar_id, role_group_id):
    buzz_words = get_buzz_words(role_group_id)

    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute('select post_uuid, post_text,post_id from post_details where calendar_id="{calendar_id}"'.format(
            calendar_id=calendar_id))
        results = list()
        for row in cur:
            score = get_score(row['post_text'], buzz_words)
            results.append((row['post_uuid'], role_group_id, score, calendar_id, row['post_id']))

    with conn.cursor() as cur:
        cur.execute('DELETE FROM post_score WHERE calendar_id="{calendar_id}" and role_group_id={rg_id}'.format(calendar_id=calendar_id, rg_id=role_group_id))
        conn.commit()
        cur.executemany(
            """INSERT INTO post_score (post_uuid, role_group_id, score, calendar_id, post_id)
            VALUES (%s, %s, %s, %s, %s)""", results)
        conn.commit()


def get_buzz_words(role_group_id):
    with conn.cursor() as cur:
        cur.execute(
            'SELECT buzz_words from role_groups where role_group_id={rg_id}'.format(rg_id=role_group_id))
        for row in cur:
            text = row[0]
    buzz_words = ast.literal_eval(text)
    return buzz_words


def get_role_group_ids():
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute('select role_group_id from hn_jobs.role_groups')
        res = cur.fetchall()
    return [x['role_group_id'] for x in res]


def lambda_handler(event, context):
    role_group_ids = get_role_group_ids()

    for rg_id in role_group_ids:
        score_and_insert(calendar_id=event['calendar_id'], role_group_id=rg_id)

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
