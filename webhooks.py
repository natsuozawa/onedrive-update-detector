from flask import request, redirect
import requests

import csv
from datetime import datetime, timedelta
import threading
import os

from app import app
from tokens import request_tokens, read_tokens
from files import retrieve_changes
from logger import logger

@app.route('/webhooks/new')
def webhook():
    if 'ACCESS_TOKEN' not in app.config or app.config['ACCESS_TOKEN'] == '':
        # url_for does not work in this setting for an unknown reason.
        return redirect('/' + '?redirect_to=' + request.path)

    return create_webhook(app.config['APPLICATION_URL'] + '/webhooks/notify')

"""
Create a new webhook subscription at the notification_url.
Path should be the path of the directory to monitor. Leave empty for root.
"""
def create_webhook(notification_url):
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
        'resource': '/me/drive/special/approot',
        'notificationUrl': notification_url,
        'expirationDateTime': expiration_date_time.strftime('%Y-%m-%dT%H:%M:%S.000000Z')
    }

    r = requests.post(url=url, headers=headers, json=data)
    write_webhook(r.json())
    return r.json()

@app.before_first_request
def update_all_webhooks_if_token():
    if read_tokens():
        status, _ = request_tokens(refresh=True)
        if status:
            # Run this on a separate thread so that
            # when Microsoft sends a request to /webhooks/notify to confirm the endpoint
            # the request is not blocked by this function.
            thread = threading.Thread(target=update_all_webhohoks)
            thread.start()

def update_all_webhohoks():
    if 'webhooks.csv' in os.listdir():
            with open('webhooks.csv', 'r+') as f:
                cr = csv.reader(f)
                for row in cr:
                    update_webhook(row[0])

def update_webhook(webhook_id):
    if 'ACCESS_TOKEN' not in app.config or app.config['ACCESS_TOKEN'] == '':
        status, _ = request_tokens(refresh=True)
        if not status:
            return False

    url = 'https://graph.microsoft.com/v1.0/subscriptions/' + webhook_id
    headers = {'Authorization': 'Bearer ' + app.config['ACCESS_TOKEN']}

    expiration_date_time = datetime.now() + timedelta(29)
    data = {
        'expirationDateTime': expiration_date_time.strftime('%Y-%m-%dT%H:%M:%S.000000Z')
    }

    r = requests.patch(url=url, headers=headers, json=data)

    return 'expirationDateTime' in r.json()

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
    logger.debug("Webhook notification received.")
    retrieve_changes()
    return request.args.get('validationToken', '')
