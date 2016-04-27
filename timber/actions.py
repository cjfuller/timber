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
MOVE_CURSOR = ActionType('MOVE_CURSOR')
LOADING = ActionType('LOADING')
RENDER = ActionType('RENDER')
VIEW = ActionType('VIEW')
LOG_LEVEL = ActionType('LOG_LEVEL')
SET_INPUT_MODE = ActionType('SET_INPUT_MODE')
COMMAND_APPEND = ActionType('COMMAND_APPEND')
COMMAND_BACKSPACE = ActionType('COMMAND_BACKSPACE')
COMMAND_CLEAR = ActionType('COMMAND_CLEAR')
COMMAND_RUN = ActionType('COMMAND_RUN')


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


def move_cursor(x=0, y=0):
    return {
        'type': MOVE_CURSOR,
        'x': x,
        'y': y,
    }


def loading():
    return {'type': LOADING}


def render():
    return {'type': RENDER}


def set_view(viewname):
    return {
        'type': VIEW,
        'view': viewname,
    }


def set_log_level(level):
    return {
        'type': LOG_LEVEL,
        'level': level,
    }


def set_input_mode(mode):
    return {
        'type': SET_INPUT_MODE,
        'mode': mode,
    }


def append_to_command(partial_command):
    return {
        'type': COMMAND_APPEND,
        'text': partial_command,
    }


def backspace_command():
    return {'type': COMMAND_BACKSPACE}


def clear_command():
    return {'type': COMMAND_CLEAR}


def process_command(command):
    return {
        'type': COMMAND_RUN,
        'command': command,
    }
