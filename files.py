from flask import redirect, request
import requests

from app import app
from tokens import request_tokens

@app.route('/download_file/<item_id>')
def retrieve_file(item_id):
    if 'ACCESS_TOKEN' not in app.config or app.config['ACCESS_TOKEN'] == '':
        return redirect('/' + '?redirect_to=' + request.path)
    url = 'https://graph.microsoft.com/v1.0/me/drive/items/' + item_id + '/content'
    return retrieve_as(url, json=False)

@app.route('/retrieve_files_at/<path>')
def retrieve_children(path):
    if 'ACCESS_TOKEN' not in app.config or app.config['ACCESS_TOKEN'] == '':
        return redirect('/' + '?redirect_to=' + request.path)
    url = 'https://graph.microsoft.com/v1.0/me/drive/special/approot:/' + path + ':/children'
    return retrieve_as(url, json=True)

def retrieve_as(url, json=False):
    if 'ACCESS_TOKEN' not in app.config or app.config['ACCESS_TOKEN'] == '':
        status, _ = request_tokens(refresh=True)
        if not status:
            return {} if json else ''

    headers = {'Authorization': 'Bearer ' + app.config['ACCESS_TOKEN']}

    r = requests.get(url=url, headers=headers)
    return r.json() if json else r.text
