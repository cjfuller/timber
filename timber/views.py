import json

import funcy
from funcy import get_in

echo = funcy.partial(print, end='', flush=True)


def log_level_indicators(t, skip_initial=False):
    initial = '' if skip_initial else ' '
    return {
        'DEBUG': t.white_on_black(initial + 'λ '),
        'INFO': t.white_on_blue(initial + 'i '),
        'WARNING': t.black_on_yellow(initial + '! '),
        'ERROR': t.white_on_red(initial + '→ '),
        'CRITICAL': t.white_on_magenta(initial + '▶ '),
    }


def fixed_width(n_cols, item):
    return (str(item) + (' ' * n_cols))[:n_cols]


def format(t, log_entry, is_curr_line=False):
    status = fixed_width(3, log_entry['status'] or '---')
    if status.startswith('2'):
        status = t.blue(status)
    elif status.startswith('4'):
        status = t.yellow(status)
    elif status.startswith('5'):
        status = t.red(status)

    if log_entry['timestamp']:
        timestamp = log_entry['timestamp'].strftime('%H:%M:%S.%f')[:-3]

    return ' '.join([
        log_level_indicators(
            t, skip_initial=is_curr_line)[log_entry['severity']],
        fixed_width(12, timestamp),
        fixed_width(11, log_entry['version']),
        fixed_width(7, log_entry['module']),
        '',
        status,
        fixed_width(4, log_entry['method']),
        # TODO: to edge of terminal.
        fixed_width(80, log_entry['resource']),
    ])


def current_line_start(term):
    return term.black_on_cyan('▶')


def current_line_end(term):
    return term.black_on_cyan('◀')


def render_status_line(term, status):
    echo(term.black_on_yellow(status))


def _render_command_line(term, state):
    if state.get('command_buffer', None) is None:
        return

    echo(term.move(term.height - 1, 0))
    echo(':')
    echo(state['command_buffer'])


def _render_shared(state):
    term = state['term']
    echo(term.clear)
    echo(term.move(0, 0))
    render_status_line(term, state.get('status', ''))
    _render_command_line(term, state)


def _render_logs(state):
    term = state['term']
    _render_shared(state)
    y = get_in(state, ['cursor', 'y'], 0)
    # TODO: need to account for sort direction eventually
    for row_index, log in enumerate(
            funcy.take(term.height - 2, state.get('logs', []))):
        echo(term.move(row_index + 1, 0))
        logline = format(term, log)
        echo(logline)
        if y == row_index:
            echo(term.move(row_index + 1, term.width - 1))
            echo(current_line_end(term))
            echo(term.move(row_index + 1, 0))
            echo(current_line_start(term))


def _format_message(term, message):
    ts = message['time'][11:23]
    severity = log_level_indicators(term)[message['severity']]
    text = message['logMessage'].split('\n')
    if len(text) > 7:
        text = text[0:3] + ['...'] + text[-3:]
    echo(severity + ' ' + ts + ' ')
    for line in text:
        echo(line)
        echo(term.move_down())
        echo(term.move_x(0))


def _render_expanded_view(state):
    _render_shared(state)
    term = state['term']
    y = get_in(state, ['cursor', 'y'], 0)
    log_entry = state['logs'][y]
    echo('Detail for: ' + format(term, log_entry))
    echo(term.move_down())
    echo(term.move_down())
    echo(term.move_x(0))
    for i, msg in enumerate(log_entry['messages']):
        _format_message(term, msg)


views = {
    'logs': _render_logs,
    'expanded': _render_expanded_view,
}


def render_from_state(state):
    term = state.get('term')
    if term is None:
        return

    view = views[state.get('view', 'logs')]
    with term.raw(), term.hidden_cursor(), term.location(), term.keypad():
        view(state)
