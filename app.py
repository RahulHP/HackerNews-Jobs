import boto3
from functools import wraps
from config import config
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = config['app_secret_key']

cognito_client = boto3.client('cognito-idp', region_name=config['aws_region'])


def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'access_token' in session:
            return f(*args, **kwargs)
        else:
            return redirect(url_for('login'))
    return wrap


@app.route('/')
@login_required
def index():
    user = cognito_client.get_user(
        AccessToken=session['access_token']
    )
    user_sub = get_user_sub(user)
    return render_template('index.html', sub=user_sub)


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
                ClientId=config['cognito_user_pool_id'],
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
        return render_template('login.html')
    else:
        try:
            response = cognito_client.initiate_auth(
                ClientId=config['cognito_user_pool_id'],
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
        except Exception as e:
            print(e)
            return {'Code': 'Failure', 'Message': str(e)}


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
