# Timber

 A command-line log viewer for appengine logs.

# Installation

Requires python 3.5 (it makes use of async/await-based coroutines)

`pip install timber`

# Usage

`timber --config account=<your google account> project=<google cloud project id>`
(This will put these options into `~/.timberrc` so that you only have to do
this the first time, unless you want to switch projects or accounts.)

`timber`

# Keyboard commands
| Key     |  Action                                                                 |
|---------|-------------------------------------------------------------------------|
| r       | [r]efresh, fetching the latest logs                                     |
| k, j    | move up and down through the list of logs                               |
| >       | from the logs list view, get detailed information for the current log   |
| <       | from the log detail view, go back to the list of logs                   |
| q       | [q]uit the current view (detail -> logs list; logs list -> exit)        |
| Ctrl-c  | exit (gracefully)                                                       |


