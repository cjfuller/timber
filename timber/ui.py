import asyncio
import inspect

from funcy import get_in, set_in, update_in

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
    log_formatter.render_from_state(state)
    return state


def set_view(state, action):
    return set_in(state, ['view'], action['view'])


reducers[actions.SHUTDOWN] = shutdown_reducer
reducers[actions.STORE_LOGS] = store_logs_reducer
reducers[actions.SET_TERM] = set_term_reducer
reducers[actions.MOVE_CURSOR] = move_cursor_reducer
reducers[actions.LOADING] = set_loading
reducers[actions.RENDER] = do_render
reducers[actions.VIEW] = set_view


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
    await _action_queue.put(actions.render())


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
        await dispatch(actions.loading())
        await dispatch(actions.fetch_logs())
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
    elif keypress == chr(3):
        shutdown()
    if not _get_state().get('shutdown'):
        loop.create_task(input_main(term, opts))


def shutdown():
    loop.create_task(dispatch(actions.shutdown()))
    loop.call_later(0.05, lambda: loop.stop())


def ui_event_loop(term, initial_state, opts):
    with term.fullscreen(), term.raw(), term.hidden_cursor(), term.location(), term.keypad():
        term.clear()
        loop.create_task(dispatch(actions.set_term(term)))
        loop.create_task(dispatch(actions.loading()))
        loop.create_task(dispatch(actions.fetch_logs()))
        loop.create_task(drain_action_queue())
        loop.create_task(input_main(term, opts))
        loop.run_forever()
        loop.close()
