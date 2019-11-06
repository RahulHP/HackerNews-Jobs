import boto3
import pymysql
import os

client = boto3.client('ssm')
parameters = client.get_parameters_by_path(
    Path='/rds',
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


def lambda_handler(event, context):
    print("Transforming")
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute('SELECT * from post_raw where calendar = "{calendar}"'.format(calendar=event['calendar_id']))
        results = list()
        ingested_rows = 0
        transformed_rows = 0
        for row in cur:
            ingested_rows += 1
            if row['by'] == 'None' or row['text'] == 'None':
                continue
            post_uuid = '|'.join([str(event['calendar_id']), str(row['id'])])
            role = None
            company = None
            post_text = row['text']
            poster_id = row['by']
            post_time = row['time']
            parent_id = row['parent']
            calendar_id = row['calendar']
            post_id = row['id']
            results.append((post_uuid, role, company, post_text, poster_id, post_time, parent_id, calendar_id, post_id))
            transformed_rows += 1

    print("Inserting SQL")
    with conn.cursor() as cur:
        cur.execute('DELETE FROM post_details WHERE calendar_id = "{calendar}"'.format(calendar=event['calendar_id']))
        conn.commit()
        cur.executemany(
            """INSERT INTO post_details (post_uuid, role, company, post_text, poster_id, post_time, parent_id, calendar_id, post_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""", results)
        conn.commit()

    return {
        'month': event['calendar_id'],
        'ingested': ingested_rows,
        'transformed': transformed_rows
    }
