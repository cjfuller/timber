import asyncio
import inspect
import signal
import time

from funcy import set_in

from timber import actions
from timber import log_formatter


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
    print(type(action['logs']))
    newstate = set_in(state, ['logs'], action['logs'])
    log_formatter.render_from_state(newstate)
    return newstate


def set_term_reducer(state, action):
    return set_in(state, ['term'], action['terminal'])


reducers[actions.SHUTDOWN] = shutdown_reducer
reducers[actions.STORE_LOGS] = store_logs_reducer
reducers[actions.SET_TERM] = set_term_reducer


def process_action(action):
    global _store_state
    if action['type'] in reducers:
        _store_state = reducers[action['type']](_store_state, action)
    else:
        raise TypeError("Unknown action type: %s" % action['type'])

async def drain_action_queue():
    item = await _action_queue.get()
    if inspect.isawaitable(item):
        action = await(item)
    else:
        action = item
    process_action(action)
    _action_queue.task_done()
    if not _get_state().get('shutdown'):
        loop.create_task(drain_action_queue())

async def dispatch(action):
    await _action_queue.put(action)


def draw_logs(term, state, opts):
    term.clear()

    logs = sorted(state['logs'], key=lambda l: l['start_time'],
                  reversed=(opts.order == 'ASC'))
    start_index = state['visible_start']
    n_rows = term.height - UI_ROWS
    visible_logs = logs[start_index:(start_index + n_rows)]


async def read_key(term):
    with term.cbreak():
        return term.inkey(timeout=0.01)


async def input_main(term, opts):
    keypress = await read_key(term)
    if keypress == 'r':
        await dispatch(actions.fetch_logs())
    if not _get_state().get('shutdown'):
        loop.create_task(input_main(term, opts))


def shutdown():
    loop.create_task(dispatch(actions.shutdown()))
    loop.call_later(0.05, lambda: loop.stop())


def ui_event_loop(term, initial_state, opts):
    loop.add_signal_handler(signal.SIGINT, shutdown)

    with term.fullscreen():
        term.clear()
        loop.create_task(dispatch(actions.set_term(term)))
        loop.create_task(dispatch(actions.fetch_logs()))
        loop.create_task(drain_action_queue())
        loop.create_task(input_main(term, opts))
        loop.run_forever()
        loop.close()
