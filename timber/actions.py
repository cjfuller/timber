from timber import logging_service


class ActionType:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name


SHUTDOWN = ActionType('SHUTDOWN')
STORE_LOGS = ActionType('STORE_LOGS')
SET_TERM = ActionType('SET_TERM')


def store_logs(logs):
    return {
        'type': STORE_LOGS,
        'logs': logs,
    }


async def fetch_logs():
    logs = await logging_service.fetch_latest_logs()
    return store_logs(logs)


def shutdown():
    return {
        'type': SHUTDOWN,
    }


def set_term(t):
    return {
        'type': SET_TERM,
        'terminal': t,
    }
