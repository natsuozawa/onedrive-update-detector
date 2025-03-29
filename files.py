from flask import redirect, request
import requests

import os
from datetime import datetime, timedelta
from urllib.parse import quote

from app import app
from tokens import request_tokens
from logger import logger

from script import script

@app.before_first_request
def create_download_folder():
    if app.config['DOWNLOAD_LOCATION'] and not os.path.exists(app.config['DOWNLOAD_LOCATION']):
        os.makedirs(app.config['DOWNLOAD_LOCATION'])

@app.route('/update_files')
def update_files():
    res, err = retrieve_changes()
    if res:
        return 'Successful.'
    return err

"""
Approximate the behavior of downloading newly created files.
1. Retrieve the latest updates using the delta API endpoint.
2. For any file changes, keep track of the parent folder.
3. For each parent folder, retrieve the newest csv or db file in that folder. (configure file type)
4. Run custom script on these files.
Return True, None if retrieval was successful. False, res otherwise.
"""
def retrieve_changes():
    if 'ACCESS_TOKEN' not in app.config or app.config['ACCESS_TOKEN'] == '':
        return redirect('/' + '?redirect_to=' + request.path)

    folders, err = retrieve_updated_folders()
    if folders is None:
        return False, err

    for folder_id, folder_name in folders:
        res = retrieve_children(folder_id)

        if 'value' not in res:
            logger.warning(res)
            return False, res

        newest_item_id, newest_item_extension = newest_item(res['value'])
        newest_item_content = retrieve_file(newest_item_id)

        output_changes(folder_name, newest_item_extension, newest_item_content)

    return True, None

"""
Use the delta API endpoint to retrieve folders in which files were changed.
It is not possible to retrieve with more precision. (ie. retrieve folders only where files were newly created)
Returns a set with the folder id and name pairs, and a response object.
"""
def retrieve_updated_folders():
    logger.debug('Retrieving updated folders')
    if 'ACCESS_TOKEN' not in app.config or app.config['ACCESS_TOKEN'] == '':
        status, err = request_tokens(refresh=True)
        if not status:
            logger.debug('Failed to obtain tokens.')
            logger.debug(err)
            return None, err

    # Due to a bug in the API, somehow we can't initiate the delta link without arguments.
    timestamp_28_days_ago = (datetime.utcnow() - timedelta(days=28)).strftime('%Y-%m-%dT%H:%M:%SZ')
    delta_query_timestamp = quote(timestamp_28_days_ago)
    url = f'https://graph.microsoft.com/v1.0/me/drive/special/approot/delta?token={delta_query_timestamp}'

    # Use delta link if saved.
    if 'delta_link' in os.listdir():
        with open('delta_link', 'r') as f:
            delta_link = f.readline()
            if delta_link:
                url = delta_link

    headers = {'Authorization': 'Bearer ' + app.config['ACCESS_TOKEN']}

    # The response will contain a next link if there are still changes to load.
    # Otherwise, it would contain a delta link.
    # If it contains neither, it is likely an error.
    logger.info(url)
    logger.info(headers)
    r = requests.get(url, headers=headers)
    res = r.json()

    if 'error' in res:
        logger.warning("Error in retrieving the list of folders.")
        return None, res

    folders = set()

    while True:
        # There are changes to record.
        if 'value' in res:
            for item in res['value']:
                if 'file' not in item or 'parentReference' not in item:
                # if 'file' not in item or 'parentReference' not in item or 'name' not in item['parentReference']:
                    # If name is not in item, it used to mean that the item was deleted (from the last delta_link).
                    # We don't check for deletions.

                    # From around 2024 December, it looks like the parentReference does not include a name field for all items.
                    continue

                file_types = app.config['FILE_TYPES'].split(',')

                # The file name ends with one of the configured file types.
                if any([item['name'].endswith(file_type) for file_type in file_types]):
                    folder_path = item['parentReference']['path']
                    folder_name = folder_path.split('/')[-1]
                    folder = (item['parentReference']['id'], folder_name)
                    folders.add(folder)

        if '@odata.deltaLink' in res:
            break
        elif '@odata.nextLink' in res:
            next_link = res['@odata.nextLink']
            r = requests.get(url + '(token=\'' + next_link + '\')', headers=headers)
            res = r.json()
        else:
            return None, res

    # Record the delta link for future use.
    with open('delta_link', 'w+') as f:
        f.write(res['@odata.deltaLink'])

    if len(folders) == 0:
        return None, {"message": "Nothing updated."}
    return folders, None

"""
Given a list of items, return the item with the newest creation date time
such that the item file type is in the FILE_TYPES configuration.
Returns the item id and file type extension pair. Returns (None, None) if there is no such item.
"""
def newest_item(items):
    newest_item_id = None
    newest_item_extension = None
    # Initialize to the earliest datetime.
    newest_created_date_time = datetime(1970, 1, 1)
    for item in items:
        if 'file' not in item or 'name' not in item or 'id' not in item:
            continue

        file_types = app.config['FILE_TYPES'].split(',')

        # Not using the any function here to record the file type.
        for file_type in file_types:
            # The file name has one of the configured file type extensions.
            # Note: .endswith is not used here to accommodate certain Android export issues where .db is exported as .db.txt.
            # TODO: fix once the issue is resolved.
            if file_type in item['name']:
                # The API used to return millisecond or nanosecond values for the createdDateTime field.
                try:
                    item_created_date_time = datetime.strptime(item['createdDateTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
                except ValueError:
                    item_created_date_time = datetime.strptime(item['createdDateTime'], '%Y-%m-%dT%H:%M:%SZ')

                # The current item is the newest so far.
                if newest_created_date_time < item_created_date_time:
                    newest_item_id = item['id']
                    newest_item_extension = file_type
                    newest_created_date_time = item_created_date_time
                break

    return newest_item_id, newest_item_extension


# @app.route('/download_file/<item_id>')
def retrieve_file(item_id):
    if 'ACCESS_TOKEN' not in app.config or app.config['ACCESS_TOKEN'] == '':
        return redirect('/' + '?redirect_to=' + request.path)
    url = 'https://graph.microsoft.com/v1.0/me/drive/items/' + item_id + '/content'
    return retrieve_as(url, json=False)

# @app.route('/retrieve_files_at/<item_id>')
def retrieve_children(item_id):
    if 'ACCESS_TOKEN' not in app.config or app.config['ACCESS_TOKEN'] == '':
        return redirect('/' + '?redirect_to=' + request.path)
    url = 'https://graph.microsoft.com/v1.0/me/drive/items/' + item_id + '/children'
    return retrieve_as(url, json=True)

def retrieve_as(url, json=False):
    if 'ACCESS_TOKEN' not in app.config or app.config['ACCESS_TOKEN'] == '':
        status, _ = request_tokens(refresh=True)
        if not status:
            return {} if json else ''

    headers = {'Authorization': 'Bearer ' + app.config['ACCESS_TOKEN']}

    r = requests.get(url=url, headers=headers)
    return r.json() if json else r.content

@app.route('/remove_delta')
def remove_delta():
    if 'delta_link' in os.listdir():
        os.remove('delta_link')
        return 'Successful.'
    return 'No delta_link file to remove.'

def output_changes(folder_name, newest_item_extension, newest_item_content):
    # Save downloaded content under the folder name + file type extension.
    with open(app.config['DOWNLOAD_LOCATION'] + '/' + folder_name + newest_item_extension, 'w+b') as f:
        f.write(newest_item_content)
    script(folder_name, newest_item_extension)

