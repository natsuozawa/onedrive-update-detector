from flask import Flask, render_template, request, redirect, url_for
import requests

import os

app = Flask(__name__)
app.config.from_pyfile('app.cfg')

@app.route('/')
def index():
    if read_tokens():
        request_tokens(refresh=True)
        return redirect(url_for('update_files'))

    return render_template('index.html', tenant=app.config['TENANT'], application_id=app.config['APPLICATION_ID'], redirect_url=app.config['REDIRECT_URL'], scope=permission_scope()) 

@app.route('/register_token')
def register_token():
    status, err = request_tokens(refresh=False, code=request.args.get('code', type=str))
    if status:
        return redirect(url_for('update_files'))
    return err['error_description']

@app.route('/update_files')
def update_files():
    return 'Work in progress.'

"""
Send a POST request to obtain access and refresh tokens from Microsoft.
code: 
"""
def request_tokens(refresh=False, code=''):
    url = 'https://login.microsoftonline.com/' + app.config['TENANT'] + '/oauth2/v2.0/token'
    data = {
        'client_id': app.config['APPLICATION_ID'], 
        'scope': permission_scope(include_offline_acess=False),
        'grant_type': 'refresh_token' if refresh else 'authorization_code',
        'redirect_uri': app.config['REDIRECT_URL'],
        'client_secret': app.config['CLIENT_SECRET']
    }

    if refresh:
        data['refresh_token'] = app.config['REFRESH_TOKEN']
    else:
        data['code'] = code

    r = requests.post(url, data = data)
    res = r.json()

    if 'error' in res:
        return False, res

    app.config['ACCESS_TOKEN'] = res['access_token']

    if 'refresh_token' in res:
        app.config['REFRESH_TOKEN'] = res['refresh_token']

    write_tokens()
    return True, None

"""
Create permission scope string.
"""
def permission_scope(include_offline_acess=True):
    permissions = ['files.read', 'user.read']
    if include_offline_acess:
        permissions.append('offline_acess')
    return "%20".join(permissions)

"""
Read refresh and access tokens from the refresh_token and access_token files.
If they do not exist or are empty, return False. 
Otherwise, read the tokens into the configuration files and return True.
"""
def read_tokens():
    if 'refresh_token' in os.listdir() and 'access_token' in os.listdir():
        with open('refresh_token', 'r') as f:
            t = f.readline()
            if t:
                app.config['REFRESH_TOKEN'] = t
            else:
                return False
        with open('access_token', 'r') as f:
            t = f.readline()
            if t:
                app.config['ACCESS_TOKEN'] = t
            else:
                return False
        return True
    return False

"""
Write refresh and access tokens into the refresh_token and access_token files.
"""
def write_tokens():
    with open('refresh_token', 'w+') as f:
        f.write(app.config['REFRESH_TOKEN'])
    with open('access_token', 'w+') as f:
        f.write(app.config['ACCESS_TOKEN'])