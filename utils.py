import boto3

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