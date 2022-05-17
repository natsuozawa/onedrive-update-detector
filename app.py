from flask import Flask, render_template, request, redirect, url_for
import requests

import os, csv
from datetime import datetime, timedelta

app = Flask(__name__)
app.config.from_pyfile('app.cfg')

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
    permissions = ['offline_access', 'user.read', 'files.read']
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

@app.route('/download_file/<item_id>')
def retrieve_file(item_id):
    if 'ACCESS_TOKEN' not in app.config or app.config['ACCESS_TOKEN'] == '':
        # url_for does not work in this setting for an unknown reason.
        return redirect('/' + '?redirect_to=' + request.path)
    url = 'https://graph.microsoft.com/v1.0/me/drive/items/' + item_id + '/content'
    return retrieve_as(url, json=False)
    
@app.route('/retrieve_files_at/<path>')
def retrieve_children(path):
    if 'ACCESS_TOKEN' not in app.config or app.config['ACCESS_TOKEN'] == '':
        # url_for does not work in this setting for an unknown reason.
        return redirect('/' + '?redirect_to=' + request.path)
    url = 'https://graph.microsoft.com/v1.0/me/drive/root:/' + path + ':/children'
    return retrieve_as(url, json=True)

def retrieve_as(url, json=False):
    if 'ACCESS_TOKEN' not in app.config or app.config['ACCESS_TOKEN'] == '':
        status, _ = request_tokens(refresh=True)
        if not status:
            return {} if json else ''
    
    headers = {'Authorization': 'Bearer ' + app.config['ACCESS_TOKEN']}

    r = requests.get(url=url, headers=headers)
    return r.json() if json else r.text
 
@app.route('/webhooks/new')
def webhook():
    if 'ACCESS_TOKEN' not in app.config or app.config['ACCESS_TOKEN'] == '':
        # url_for does not work in this setting for an unknown reason.
        return redirect('/' + '?redirect_to=' + request.path)

    return create_webhook(request.args.get('path', '', type=str), app.config['NOTIFICATION_URL'])

"""
Create a new webhook subscription at the notification_url. 
Path should be the path of the directory to monitor. Leave empty for root.
"""
def create_webhook(path, notification_url):
    if 'ACCESS_TOKEN' not in app.config or app.config['ACCESS_TOKEN'] == '':
        status, _ = request_tokens(refresh=True)
        if not status:
            return {} 

    url = 'https://graph.microsoft.com/v1.0/subscriptions'    
    headers = {'Authorization': 'Bearer ' + app.config['ACCESS_TOKEN']}

    # Microsoft allows a maximum of 30 days. Subtract 1 to allow timezone differences.
    expiration_date_time = datetime.now() + timedelta(29)

    data = {
        'changeType': 'updated',
        'resource': '/me/drive/root/' + path,
        'notificationUrl': notification_url,
        'expirationDateTime': expiration_date_time.strftime('%Y-%m-%dT%H:%M:%S.000000Z')
    }

    print(data)
    r = requests.post(url=url, headers=headers, json=data)
    write_webhook(r.json())
    return r.json()

@app.route("/webhooks/delete/<webhook_id>")
def drop_webhook(webhook_id):
    if 'ACCESS_TOKEN' not in app.config or app.config['ACCESS_TOKEN'] == '':
        # url_for does not work in this setting for an unknown reason.
        return redirect('/' + '?redirect_to=' + request.path)
    if delete_webhook(webhook_id):
        return 'Success.'
    return 'Failed to delete webhook.'

def delete_webhook(webhook_id):
    if 'ACCESS_TOKEN' not in app.config or app.config['ACCESS_TOKEN'] == '':
        status, _ = request_tokens(refresh=True)
        if not status:
            return False

    url = 'https://graph.microsoft.com/v1.0/subscriptions/' + webhook_id
    headers = {'Authorization': 'Bearer ' + app.config['ACCESS_TOKEN']}

    r = requests.delete(url=url, headers=headers)
    return r.status_code == 204

def write_webhook(webhook_response):
    if 'id' not in webhook_response:
        return
    
    with open('webhooks.csv', 'a+') as f:
        cw = csv.writer(f)
        cw.writerow([webhook_response['id'], webhook_response['resource']])

@app.route('/webhooks/notify', methods=['POST'])
def webhook_receive_notification():
    return request.args.get('validationToken')
    
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)