import subprocess
import time
import os
import boto3
from typing import List
from boto3.dynamodb.table import TableResource

def get_ssm_dict(path):
    ssm_client = boto3.client('ssm', region_name='us-east-1')
    parameters = ssm_client.get_parameters_by_path(
        Path=path, Recursive=True)
    config = dict()
    if 'Parameters' in parameters and len(parameters.get('Parameters')) > 0:
        params = parameters.get('Parameters')
        for param in params:
            param_path_array = param.get('Name').split("/")
            section_name = param_path_array[-1]
            config_values = param.get('Value')
            config[section_name] = config_values
    return config


dynamodb_config = get_ssm_dict('/{env}/dynamodb'.format(env=os.environ.get('ENV', 'test')))

dynamodb_client = boto3.resource('dynamodb', region_name='us-east-1')
user_role_group_id_table = dynamodb_client.Table(dynamodb_config['user_rolegroupid'])
user_processed_post_table = dynamodb_client.Table(dynamodb_config['user_latest_posts'])
user_stage_table = dynamodb_client.Table(dynamodb_config['user_post_stage'])

rds_config = get_ssm_dict('/rds')
test_db = 'hn_jobs_test'
cf_client = boto3.client('cloudformation', region_name='us-east-1')


def check_stack_status(stackid: str):
    try:
        response = cf_client.describe_stacks(
            StackName=stackid
        )
        status = response['Stacks'][0]['StackStatus']
        return status
    except Exception as e:
        print(e)
        print(type(e))
        return None


def get_template_string(template_file: str):
    with open(os.path.join(os.getcwd(), 'cloudformation', template_file), 'r') as f:
        template = f.read()
    return template


def delete_stack(stack_name, sleep_time=120):
    print('Deleting stack : %s' % stack_name)
    cf_client.delete_stack(
        StackName=stack_name
    )
    print('Waiting %d seconds' % sleep_time)
    time.sleep(sleep_time)

def create_dynamodb_tables():
    stack_name = 'userdatabasetest'
    template = get_template_string('user_database.yaml')
    current_status = check_stack_status(stack_name)
    if current_status in ('CREATE_COMPLETE', 'CREATE_IN_PROGRESS'):
        print('Stack %s already exists.' % stack_name)
        delete_stack(stack_name)
    try:
        print('Creating stack %s' % stack_name)
        response = cf_client.create_stack(
            StackName=stack_name,
            TemplateBody=template,
            Parameters=[
                {
                    'ParameterKey': 'env',
                    'ParameterValue': 'test'
                }
            ]
        )
    except Exception as e:
        print(e)
        print(type(e))
    wait_time = 60
    print('Waiting %d seconds for tables to be created' % wait_time)
    time.sleep(wait_time)

    current_status = check_stack_status(response['StackId'])
    if current_status in ('CREATE_IN_PROGRESS'):
        print('Waiting %d for tables to be created' % wait_time)
        time.sleep(wait_time)
    print("Fin")


def insert_dynamodb_data():
    print("Inserting DyanmoDB data")
    setup_get_post_ids_in_view()
    setup_get_view()
    print("Fin")

def create_rds_tables():
    print("Creating RDS tables")
    create_table_command = "mysql --user={user} --password={passwd} --port {port} --host={host} {db} < {sqlfile}" \
        .format(user=rds_config['name'], host=rds_config['host'], passwd=rds_config['password'], db=test_db,
                port=rds_config['port'], sqlfile=os.path.join(os.getcwd(), 'tests', 'test_db.sql'))
    subprocess.run(create_table_command, shell=True)


def load_rds_data():
    print("Loading RDS tables")
    mysqlimport_command = '''
    mysqlimport --local --compress --user={user} --password={passwd} --port {port} --host={host} \
    --fields-terminated-by=',' --fields-optionally-enclosed-by='"' {db} {table}
    '''
    data_dir = os.path.join(os.getcwd(), 'tests', 'data')
    for table in os.listdir(data_dir):
        print(table)
        subprocess.run(
            mysqlimport_command.format(user=rds_config['name'], host=rds_config['host'], passwd=rds_config['password'],
                                       db=test_db, port=rds_config['port'], table=os.path.join(data_dir, table)),
            shell=True)


def create_rds_data():
    create_rds_tables()
    load_rds_data()


def insert_items(table: TableResource, items: List[dict]):
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(
                Item=item
            )


def setup_get_post_ids_in_view():
    user_id = 'non_empty_user_postidview'
    calendar_id = 'nov_2019'
    stage_id = 99
    calendar_stage_uuid = '|'.join([calendar_id, str(stage_id)])
    post_ids = [x for x in range(1, 5)]
    items = [{'user_id': user_id, 'post_id': str(x), 'calendar_stage_uuid': calendar_stage_uuid} for x in post_ids]
    insert_items(user_stage_table, items)


def setup_get_view():
    user_id = 'non_empty_view_user'
    calendar_id = 'nov_2019'
    stage_id = 99
    calendar_stage_uuid = '|'.join([calendar_id, str(stage_id)])
    post_ids = [1, 2, 4, 6]
    items = [{'user_id': user_id, 'post_id': str(x), 'calendar_stage_uuid': calendar_stage_uuid} for x in post_ids]
    insert_items(user_stage_table, items)

    rolegroup = [{'user_id': user_id, 'role_group_id': 1}]
    insert_items(user_role_group_id_table, rolegroup)


if __name__ == '__main__':
    create_dynamodb_tables()

    insert_dynamodb_data()
    create_rds_data()
