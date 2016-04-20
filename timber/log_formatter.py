import datetime
import time

import blessed
from funcy import get_in


def log_level_indicators(t):
    return {
        'DEBUG': t.white_on_black(' λ '),
        'INFO': t.white_on_blue(' i '),
        'WARNING': t.black_on_yellow(' ! '),
        'ERROR': t.white_on_red(' → '),
        'CRITICAL': t.white_on_magenta(' ▶ '),
    }


# log_entry is an entry as defined at
# https://cloud.google.com/logging/docs/api/ref_v2beta1/rest/v2beta1/LogEntry
def format(t, log_entry):
    def get_in_log(keylist, default):
        return get_in(log_entry, keylist, default)

    severity = get_in_log(['metadata', 'severity'], 'DEBUG')
    status = str(get_in_log(['httpRequest', 'status'], '---'))
    if status.startswith('2'):
        status = t.blue(status)
    elif status.startswith('4'):
        status = t.yellow(status)
    elif status.startswith('5'):
        status = t.red(status)
    method = get_in_log(['protoPayload', 'method'], '')
    resource = get_in_log(['protoPayload', 'resource'], '')[:80]
    ts = get_in_log(['metadata', 'timestamp'], None)
    if ts:
        utc_offset_s = time.timezone
        dst_offset_s = 3600 if time.localtime().tm_isdst else 0
        total_offset = utc_offset_s - dst_offset_s
        ts = (
            datetime.datetime.strptime(ts, '%Y-%m-%dT%H:%M:%S.%fZ') -
            datetime.timedelta(seconds=total_offset)).strftime(
                '%H:%M:%S.%f')[:-3]
    return ' '.join([
        log_level_indicators(t)[severity],
        ts or ' ' * 12,
        '',
        status,
        (method + ' '*4)[:4],
        resource,
    ])


def render_from_state(state):
    for log in state['logs']:
        print(format(state['term'], log))
