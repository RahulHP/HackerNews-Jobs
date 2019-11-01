import boto3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session
import os
import requests
from utils import get_ssm_dict

app_config = get_ssm_dict('/{env}/app'.format(env=os.environ['ENV']))
cognito_config = get_ssm_dict('/{env}/cognito'.format(env=os.environ['ENV']))

app = Flask(__name__)

app.secret_key = app_config['sessionkey']
base_url = 'http://{hostname}:{port}'.format(hostname=app_config['backendhost'], port=app_config['backendport'])
cognito_client = boto3.client('cognito-idp', region_name='us-east-1')

STAGES = [['0', 'New', None],
          ['1', 'Saved', 'Save Job'],
          ['2', 'Applied', 'Applied'],
          ['3', 'Trash', 'Trash Job']]

r = requests.get('{base_url}/calendar'.format(base_url=base_url))
MONTHS = [i['month'] for i in r.json()['results']]


# TODO - What if access token has expired?
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'access_token' in session:
            return f(*args, **kwargs)
        else:
            return redirect(url_for('login'))
    return wrap


@app.route('/select_rolegroupid', methods=['GET', 'POST'])
@login_required
def select_rolegroupid():
    if request.method == 'GET':
        role_groups = requests.get('{base_url}/role_groups'.format(base_url=base_url))
        return render_template('select_rolegroupid.html', role_groups=role_groups.json()['role_groups'])
    else:
        user = cognito_client.get_user(
            AccessToken=session['access_token']
        )
        user_sub = get_user_sub(user)
        payload = {'role_group_id': request.form['role_group_selector']}
        requests.post('{base_url}/users/{user_id}/rolegroupid'.format(base_url=base_url, user_id=user_sub), data=payload)
        return redirect(url_for('index'))


@app.route('/view', methods=['GET'])
@login_required
def view():
    user = cognito_client.get_user(
        AccessToken=session['access_token']
    )
    user_sub = get_user_sub(user)

    calendar_id = request.args.get('calendar_id', MONTHS[-1])
    stage_id = request.args.get('stage_id', 0)

    requests.post('{base_url}/users/{user_id}/calendar/{calendar_id}/update_posts'.format(base_url=base_url, user_id=user_sub,calendar_id=calendar_id))

    jobs = requests.get('{base_url}/users/{user_id}/calendar/{calendar_id}/stage/{stage_id}/view'.format(base_url=base_url,user_id=user_sub,calendar_id=calendar_id,stage_id=stage_id))
    return render_template('view.html', posts=jobs.json()['results'], calendar_id=calendar_id, stage_id=stage_id, stages=STAGES, calendar=MONTHS)

@app.route('/')
@login_required
def index():
    user = cognito_client.get_user(
        AccessToken=session['access_token']
    )
    user_sub = get_user_sub(user)
    role_group_id = requests.get('{base_url}/users/{user_id}/rolegroupid'.format(base_url=base_url, user_id=user_sub)).json()
    if role_group_id['role_group_id'] is None:
        return redirect(url_for('select_rolegroupid'))
    return redirect(url_for('view'))


@app.route('/update_post', methods=['POST'])
def update_post_stage():
    user = cognito_client.get_user(
        AccessToken=session['access_token']
    )
    user_sub = get_user_sub(user)
    payload = request.form
    requests.post('{base_url}/users/{user_id}/posts'.format(base_url=base_url, user_id=user_sub), data=payload)
    return {'code':200}

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'GET':
        if 'challenge_session' in session:
            return render_template('reset_password.html')
        else:
            return redirect(url_for('login'))
    else:
        try:
            if request.form['password'] != request.form['confirm_password']:
                return redirect(url_for('reset_password'))
            response = cognito_client.respond_to_auth_challenge(
                ClientId=cognito_config['userpoolid'],
                ChallengeName='NEW_PASSWORD_REQUIRED',
                Session=session['challenge_session'],
                ChallengeResponses={
                    'USERNAME': session['challenge_username'],
                    'NEW_PASSWORD': request.form['password']
                }
            )
            if 'AuthenticationResult' in response:
                del session['challenge_session']
                del session['challenge_username']
                access_token = response['AuthenticationResult']['AccessToken']
                session['access_token'] = access_token
                return redirect(url_for('index'))
            return response
        except Exception as e:
            return {'Code': 'Failure', 'Message': str(e)}


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        session.clear()
        return render_template('login.html', error=None)
    else:
        try:
            response = cognito_client.initiate_auth(
                ClientId=cognito_config['userpoolid'],
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': request.form['username'],
                    'PASSWORD': request.form['password']
                }
            )
            if 'ChallengeName' in response and response['ChallengeName'] == 'NEW_PASSWORD_REQUIRED':
                session['challenge_session'] = response['Session']
                session['challenge_username'] = response['ChallengeParameters']['USER_ID_FOR_SRP']
                return redirect(url_for('reset_password'))
            if 'AuthenticationResult' in response:
                access_token = response['AuthenticationResult']['AccessToken']
                session['access_token'] = access_token
                return redirect(url_for('index'))
            return response
        except cognito_client.exceptions.NotAuthorizedException:
            error = 'Wrong Username/Password'
            return render_template('login.html', error=error)
        except cognito_client.exceptions.UserNotFoundException:
            error = 'User Not Found'
            return render_template('login.html', error=error)
        except Exception as e:
            error = e
            return render_template('login.html', error=error)


@app.route('/logout')
@login_required
def logout():
    session.clear()
    return redirect(url_for('login'))


def get_user_sub(get_user_response):
    user_attributes = get_user_response['UserAttributes']
    for attribute in user_attributes:
        if attribute['Name'] == 'sub':
            return attribute['Value']
    raise Exception("'sub' does not exist in UserAttributes")


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8081, debug=True)
