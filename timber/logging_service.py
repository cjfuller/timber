import asyncio
import datetime
import json
import os.path
import subprocess
import time
import types

import aiohttp
from funcy import get_in

LOGS_URL_TEMPLATE = (
    'https://logging.googleapis.com/v1beta3/projects/%s/entries:list')

_config = types.SimpleNamespace()


def set_config(newconfig: types.SimpleNamespace) -> None:
    global _config
    _config = newconfig


def config() -> types.SimpleNamespace:
    return _config


def update_config(key, str, value: str) -> types.SimpleNamespace:
    setattr(_config, key, value)
    return _config


def logs_url() -> str:
    return LOGS_URL_TEMPLATE % config().project_id


def get_user() -> str:
    return config().user


def get_auth_token() -> str:
    credentials_file = os.path.expanduser('~/.config/gcloud/credentials')
    with open(credentials_file) as f:
        credentials = json.loads(f.read())
        for cred in credentials['data']:
            if cred['key']['account'] == get_user():
                return cred['credential']['access_token']


# log_entry is an entry as defined at
# https://cloud.google.com/logging/docs/api/ref_v2beta1/rest/v2beta1/LogEntry
def extract_log_data(entry):
    ts = get_in(entry, ['metadata', 'timestamp'], None)
    if ts:
        # Convert to local time
        utc_offset_s = time.timezone
        dst_offset_s = 3600 if time.localtime().tm_isdst else 0
        total_offset = utc_offset_s - dst_offset_s
        ts = (
            datetime.datetime.strptime(ts, '%Y-%m-%dT%H:%M:%S.%fZ') -
            datetime.timedelta(seconds=total_offset))
    return {
        'ip': get_in(entry, ['protoPayload', 'versionId'], None),
        'latency': get_in(entry, ['protoPayload', 'latency'], None),
        'messages': get_in(entry, ['protoPayload', 'line'], []),
        'method': get_in(entry, ['protoPayload', 'method'], None),
        'module': get_in(entry, ['protoPayload', 'moduleId']) or 'default',
        'requestId': get_in(entry, ['protoPayload', 'requestId'], None),
        'resource': get_in(entry, ['protoPayload', 'resource'], None),
        'severity': get_in(entry, ['metadata', 'severity'], 'DEBUG'),
        'status': str(get_in(entry, ['httpRequest', 'status'], '---')),
        'timestamp': ts,
        'user_agent': get_in(entry, ['protoPayload', 'userAgent'], None),
        'version': get_in(entry, ['protoPayload', 'versionId'], None),
    }


async def fetch_latest_logs():
    ts = datetime.datetime.utcnow().isoformat()
    ts = ts[:-3] + 'Z'
    severity_string = ''
    log_level = config().log_level
    if log_level:
        severity_string = 'metadata.severity>=%s ' % log_level
    log_filter = (
        'metadata.serviceName="appengine.googleapis.com" ' +
        'log="appengine.googleapis.com/request_log" ' +
        severity_string +
        'metadata.timestamp<="%s"' % ts)

    resource = getattr(config(), 'resource', None)
    if resource:
        log_filter += ' protoPayload.resource:"%s"' % resource

    version = getattr(config(), 'version', None)
    if version:
        log_filter += (
            ' metadata.labels."appengine.googleapis.com/version_id"="%s"' % (
                version))

    req = aiohttp.post(
        logs_url(),
        data=json.dumps({
            'orderBy': 'metadata.timestamp desc',
            'pageSize': 100,
            'filter': log_filter
        }),
        headers={'Authorization': 'Bearer %s' % get_auth_token()})
    async with req as resp:
        if resp.status in (401, 403):
            proc = await asyncio.create_subprocess_exec(
                'gcloud', 'auth', 'login', get_user(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
            exitstatus = await proc.wait()
            if exitstatus != 0:
                raise subprocess.CalledProcessError(
                    "gcloud exited with status %s" % exitstatus)
            return await fetch_latest_logs()
        return list(map(
            extract_log_data, (await resp.json()).get('entries', [])))
