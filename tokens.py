from flask import request, redirect, render_template
import requests

import os

from app import app

TOKEN_REFRESH_ENDPOINT = '/'

@app.route(TOKEN_REFRESH_ENDPOINT)
def index():
    if read_tokens():
        status, err = request_tokens(refresh=True)
        if status:
            redirect_to = request.args.get('redirect_to', 'update_files', type=str)
            return redirect(redirect_to)
        return err['error_description']

    return render_template('index.html', tenant=app.config['TENANT'], application_id=app.config['APPLICATION_ID'], redirect_url=app.config['REDIRECT_URL'], scope=permission_scope())

@app.route('/register_token')
def register_token():
    status, err = request_tokens(refresh=False, code=request.args.get('code', type=str))
    if status:
        redirect_to = request.args.get('redirect_to', 'update_files', type=str)
        return redirect(redirect_to)
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

    # It is not clear whether we need to include the scope in this request.
    # In https://docs.microsoft.com/en-us/onedrive/developer/rest-api/getting-started/graph-oauth ,
    # it does not say that scope is required.
    # However, in https://docs.microsoft.com/en-us/graph/auth-v2-user , the scope is required for the same endpoint.
    # It seems like it works without the scope.
    data = {
        'client_id': app.config['APPLICATION_ID'],
        'grant_type': 'refresh_token' if refresh else 'authorization_code',
        'redirect_uri': app.config['REDIRECT_URL'],
        'client_secret': app.config['CLIENT_SECRET']
    }

    if refresh:
        data['refresh_token'] = app.config['REFRESH_TOKEN']
    else:
        data['code'] = code

    r = requests.post(url, data=data)
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
def permission_scope():
    permissions = ['offline_access', 'user.read', 'files.readwrite']
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
    with open('access_token', 'w+') as f:
        f.write(app.config['ACCESS_TOKEN'])
    if 'REFRESH_TOKEN' in app.config:
        with open('refresh_token', 'w+') as f:
            f.write(app.config['REFRESH_TOKEN'])

