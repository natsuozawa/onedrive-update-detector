from flask import redirect, request
import requests

from app import app
from tokens import request_tokens

@app.route('/retrieve_updates')
def ret():
    if retrieve_updates():
        return 'Done.'
    return 'Not done.'

def retrieve_updates():
    if 'ACCESS_TOKEN' not in app.config or app.config['ACCESS_TOKEN'] == '':
        status, _ = request_tokens(refresh=True)
        if not status:
            return False

    url = 'https://graph.microsoft.com/v1.0/me/drive/special/approot/delta'

    with open('delta_link', 'r+') as f:
        delta_link = f.readline()
        if delta_link:
            url = delta_link

    headers = {'Authorization': 'Bearer ' + app.config['ACCESS_TOKEN']}

    r = requests.get(url, headers=headers)
    res = r.json()
    if '@odata.nextLink' in res:
        next_link = res['@odata.nextLink']
        while True:
            repeat_r = requests.get(url + '(token=\'' + next_link + '\')', headers=headers)
            repeat_res = repeat_r.json()
            if '@odata.deltaLink' in repeat_res:
                res = repeat_res
                break
            if '@odata.nextLink' in repeat_res:
                next_link = repeat_res['@odata.nextLink']
                continue
            return False
    elif '@odata.deltaLink' in res:
        pass
    else:
        return False

    with open('delta_link', 'w+') as f:
        f.write(res['@odata.deltaLink'])
    return True

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
