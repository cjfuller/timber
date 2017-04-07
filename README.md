# Timber

 A command-line log viewer for appengine logs.

# Installation

Grab one of the precompiled binaries:

[OSX](https://storage.googleapis.com/timber-dist/osx/timber)

[linux x86_64](https://storage.googleapis.com/timber-dist/linux-x86_64/timber)

Or build from source:
```
go get cloud.google.com/go/logging
go get github.com/gizak/termui
go build timber.go
```

# Usage

Timber requires that you have gcloud credentials.
```
gcloud auth login <email>
```

Set your google cloud project id using a command line flag:
```
timber -project <my project>
```

The last value you supplied for the project id will be stored in `~/.timberrc`,
so you only need to provide the flag once, or when you want to change projects.

# Keyboard commands
| Key          |  Action                                                                 |
|--------------|-------------------------------------------------------------------------|
| r            | [r]efresh, fetching the latest logs                                     |
| k, j         | move up and down through the list of logs                               |
| K, J         | move up and down through the list of logs by 10 rows                    |
| g            | jump to the top of the list of logs                                     |
| G            | jump to the bottom of the list of logs                                  |
| > or enter   | from the logs list view, get detailed information for the current log   |
| q            | [q]uit the current view (detail -> logs list; logs list -> exit)        |
| Ctrl-c       | exit (gracefully)                                                       |
| :            | from the logs list, enter command mode with a vim-style command line    |

# Command mode

`:set level=<LEVEL>` where `<LEVEL>` is in `(DEBUG, INFO, WARNING, ERROR, CRITICAL)`:
set the log level to the specified level and re-fetch logs (defaults to ERROR on load or if unrecognized)

`:set resource=<rel URL>` will search for logs only matching the specified route (or partial route)
`:unset resource` clears a previously added resource filter


(Note that unrecognized commands are currently ignored.)

