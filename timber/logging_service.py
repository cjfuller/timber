import asyncio
import datetime
import json
import os.path
import subprocess

import aiohttp
import requests

PROJECT_ID = 'khan-academy'
LOGS_URL = (
    'https://logging.googleapis.com/v1beta3/projects/%s/entries:list'
    % PROJECT_ID)
USER = 'colin@khanacademy.org'


def get_auth_user() -> str:
    return USER


def get_auth_token() -> str:
    credentials_file = os.path.expanduser('~/.config/gcloud/credentials')
    with open(credentials_file) as f:
        credentials = json.loads(f.read())
        for cred in credentials['data']:
            if cred['key']['account'] == get_auth_user():
                return cred['credential']['access_token']


async def fetch_latest_logs():
    ts = datetime.datetime.utcnow().isoformat()
    ts = ts[:-3] + 'Z'
    log_filter = (
        'metadata.serviceName="appengine.googleapis.com" '
        'log="appengine.googleapis.com/request_log" '
        'metadata.severity>=ERROR '
        'metadata.timestamp<="%s"' % ts)
    resp = requests.post(
        LOGS_URL,
        data={
            'orderBy': 'metadata.timestamp desc',
            'pageSize': 100,
            'filter': log_filter
        },
        headers={'Authorization': 'Bearer %s' % get_auth_token()})
    if resp.status_code in (401, 403):
        subprocess.check_call(['gcloud', 'auth', 'login', USER],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
        return fetch_latest_logs()
    return resp.json().get('entries', [])
