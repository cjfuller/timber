import asyncio
import inspect
import re

from funcy import get_in, set_in, update_in

from timber import actions
from timber import views
from timber import logging_service


COMMAND = 'command_mode'
NORMAL = 'normal_mode'
UI_ROWS = 3

_store_state = {}

_action_queue = asyncio.Queue()

loop = asyncio.get_event_loop()

reducers = {}


def _get_state():
    return _store_state


def shutdown_reducer(state, action):
    return set_in(state, ['shutdown'], True)


def store_logs_reducer(state, action):
    newstate = set_in(state, ['logs'], action['logs'])
    newstate = clear_status(newstate)
    return newstate


def set_term_reducer(state, action):
    return set_in(state, ['term'], action['terminal'])


def force_in_range(value, minval, maxval):
    return min(max(value, minval), maxval - 1)


def move_cursor_reducer(state, action):
    term = state['term']
    state = update_in(
        state, ['cursor', 'x'],
        lambda x: force_in_range((x or 0) + action['x'], 0, term.width))
    state = update_in(
        state, ['cursor', 'y'],
        lambda y: force_in_range((y or 0) + action['y'], 0, term.height))
    return state


def set_loading(state, action):
    return set_in(state, ['status'], 'Loading...')


def clear_status(state):
    return set_in(state, ['status'], '')


def do_render(state, action):
    views.render_from_state(state, last_state=None)
    return state


def set_view(state, action):
    return set_in(state, ['view'], action['view'])


def set_log_level(state, action):
    return set_in(state, ['log_service_config', 'log_level'], action['level'])


def set_input_mode(state, action):
    return set_in(state, ['input_mode'], action['mode'])


def append_to_command(state, action):
    return set_in(
        state, ['command_buffer'],
        (get_in(state, ['command_buffer'], '') or '') + action['text'])


def backspace_command(state, action):
    return set_in(state, ['command_buffer'],
                  (get_in(state, ['command_buffer'], '') or '')[:-1])


def clear_command(state, action):
    return set_in(state, ['command_buffer'], None)


def run_command(state, action):
    command = action['command']
    log_re_match = re.match(
        r'set level=(ALL|DEBUG|INFO|WARNING|ERROR|CRITICAL)',
        command)
    if log_re_match:
        level = log_re_match.group(1)
        newstate = set_log_level(state, actions.set_log_level(level))
        # TODO: move to the action itself?  Probably shouldn't have
        # side-effects here.
        loop.create_task(refetch_logs())
        return newstate
    else:
        return state


reducers[actions.SHUTDOWN] = shutdown_reducer
reducers[actions.STORE_LOGS] = store_logs_reducer
reducers[actions.SET_TERM] = set_term_reducer
reducers[actions.MOVE_CURSOR] = move_cursor_reducer
reducers[actions.LOADING] = set_loading
reducers[actions.RENDER] = do_render
reducers[actions.VIEW] = set_view
reducers[actions.LOG_LEVEL] = set_log_level
reducers[actions.SET_INPUT_MODE] = set_input_mode
reducers[actions.COMMAND_APPEND] = append_to_command
reducers[actions.COMMAND_BACKSPACE] = backspace_command
reducers[actions.COMMAND_CLEAR] = clear_command
reducers[actions.COMMAND_RUN] = run_command


def process_action(action):
    global _store_state
    last_state = _store_state
    if action['type'] in reducers:
        _store_state = reducers[action['type']](_store_state, action)
    else:
        raise TypeError("Unknown action type: %s" % action['type'])
    return (last_state, _store_state)


async def drain_action_queue():
    item = await _action_queue.get()
    if inspect.isawaitable(item):
        action = await(item)
    else:
        action = item
    last_state, state = process_action(action)
    _action_queue.task_done()
    views.render_from_state(state, last_state=last_state)
    if not _get_state().get('shutdown'):
        loop.create_task(drain_action_queue())


async def dispatch(action):
    await _action_queue.put(action)


async def read_key(term):
    # TODO: (monkey-)patch blessed so that we can actually use asyncio for
    # reading characters instead of this timeout silliness.
    with term.cbreak():
        return term.inkey(timeout=0.01)


async def refetch_logs():
    await dispatch(actions.loading())
    update_log_service_config_from_state(_get_state())
    await dispatch(actions.fetch_logs())


def update_log_service_config_from_state(state):
    config = logging_service.config()
    for opt, val in state['log_service_config'].items():
        setattr(config, opt, val)


async def normal_mode_process_key(term, opts, keypress):
    if keypress == 'r':
        await refetch_logs()
    elif keypress in (term.KEY_UP, 'k'):
        await dispatch(actions.move_cursor(x=0, y=-1))
    elif keypress in (term.KEY_DOWN, 'j'):
        await dispatch(actions.move_cursor(x=0, y=1))
    elif keypress == '>':
        await dispatch(actions.set_view('expanded'))
    elif keypress == '<':
        await dispatch(actions.set_view('logs'))
    elif keypress == 'g':
        curr_y = get_in(_get_state(), ['cursor', 'y'])
        await dispatch(actions.move_cursor(y=-curr_y))
    elif keypress == 'G':
        next_y = term.height - 2
        await dispatch(actions.move_cursor(y=next_y))
    elif keypress == 'q':
        if _get_state().get('view') == 'logs':
            shutdown()
        else:
            await dispatch(actions.set_view('logs'))
    elif keypress == ':':
        await dispatch(actions.append_to_command(''))
        await dispatch(actions.set_input_mode(COMMAND))
    elif keypress == chr(3):
        shutdown()


async def command_mode_process_key(term, opts, keypress):
    if keypress.name == 'KEY_ENTER':
        await dispatch(
            actions.process_command(_get_state().get('command_buffer')))
        await dispatch(actions.clear_command())
        await dispatch(actions.set_input_mode(NORMAL))
    elif keypress.name in ('KEY_DELETE', 'KEY_BACKSPACE'):
        await dispatch(actions.backspace_command())
    elif keypress:
        str_val = '' + keypress
        await dispatch(actions.append_to_command(str_val))


def mode():
    return _get_state().get('input_mode', None)


async def input_main(term, opts):
    keypress = await read_key(term)
    if mode() == NORMAL or mode() is None:
        await normal_mode_process_key(term, opts, keypress)
    elif mode() == COMMAND:
        await command_mode_process_key(term, opts, keypress)

    if not _get_state().get('shutdown'):
        loop.create_task(input_main(term, opts))


def shutdown():
    loop.create_task(dispatch(actions.shutdown()))
    loop.call_later(0.05, lambda: loop.stop())


def ui_event_loop(term, initial_state, opts):
    with term.fullscreen(), term.raw(), term.hidden_cursor(), term.location(), term.keypad():
        term.clear()
        loop.create_task(dispatch(actions.set_log_level(
            logging_service.config().log_level)))
        loop.create_task(dispatch(actions.set_input_mode(NORMAL)))
        loop.create_task(dispatch(actions.set_term(term)))
        loop.create_task(dispatch(actions.loading()))
        loop.create_task(dispatch(actions.fetch_logs()))
        loop.create_task(drain_action_queue())
        loop.create_task(input_main(term, opts))
        loop.run_forever()
        loop.close()
