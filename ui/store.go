package ui

import "regexp"
import "time"
import "../logservice"

var dispatch = make(chan interface{}, 100)
var _state = State{
	Mode:   NormalMode,
	Cursor: Position{x: 0, y: 0},
	Status: LoadingStatus,
}

const LoadingStatus = "loading"
const OkStatus = "ok"
const ErrorStatus = "error"

const NormalMode = "normal"
const FocusMode = "focus"
const CommandMode = "command"

type Position struct {
	x int
	y int
}

type State struct {
	Shutdown      bool
	Logs          []logservice.LogEntryMin
	LogsUpdatedAt time.Time
	Cursor        Position
	Status        string
	Config        logservice.LogServiceConfig
	Mode          string
	CommandBuffer string
	Flash         string
}

func Dispatch(action interface{}) {
	dispatch <- action
}

func RefetchLogs() {
	Dispatch(LoadingAction{})
	// TODO(colin): somehow set the logservice config
	logs, err := logservice.FetchLatestLogs(LogsHeight(), _state.Config)
	if err != nil {
		Dispatch(SetErrorAction{message: err.Error()})
	} else {
		Dispatch(StoreLogsAction{logs: logs})
	}
}

var setRegexp = regexp.MustCompile("^set ([^=]+)=(.*)$")
var unsetRegexp = regexp.MustCompile("^unset (.*)$")

func processCommand(command string) {
	if matches := setRegexp.FindStringSubmatch(command); matches != nil {
		key := matches[1]
		value := matches[2]
		drawStatusLine(key)
		switch key {
		case "level":
			// TODO(colin): validate that the level is valid?
			Dispatch(SetLogLevelAction{logLevel: value})
		case "resource":
			Dispatch(SetResourceFilterAction{resource: value})
		}
	} else if matches := unsetRegexp.FindStringSubmatch(command); matches != nil {
		key := matches[1]
		switch key {
		case "level":
			Dispatch(SetLogLevelAction{logLevel: ""})
		case "resource":
			Dispatch(SetResourceFilterAction{resource: ""})
		}
	}
}

func ensureCursorInBounds(pos Position) Position {
	if pos.x < 0 {
		pos.x = 0
	}
	if pos.y < 0 {
		pos.y = 0
	}
	if pos.x >= LogsWidth() {
		pos.x = LogsWidth() - 1
	}
	if pos.y >= LogsHeight() {
		pos.y = LogsHeight() - 1
	}
	return pos
}

func handleAction(action interface{}) bool {
	switch a := action.(type) {
	case ShutdownAction:
		return true
	case LoadingAction:
		_state.Status = LoadingStatus
	case StoreLogsAction:
		_state.Logs = a.logs
		_state.Status = OkStatus
		_state.LogsUpdatedAt = time.Now().UTC()
	case AppendToCommandAction:
		_state.CommandBuffer += a.text
	case SetInputModeAction:
		_state.Mode = a.mode
	case BackspaceCommandAction:
		if len(_state.CommandBuffer) > 0 {
			_state.CommandBuffer = _state.CommandBuffer[:len(_state.CommandBuffer)-1]
		}
	case ClearCommandAction:
		_state.CommandBuffer = ""
		_state.Mode = NormalMode
	case ProcessCommandAction:
		processCommand(a.command)
	case SetLogLevelAction:
		_state.Config.LogLevel = a.logLevel
		go RefetchLogs()
	case SetResourceFilterAction:
		_state.Config.Resource = a.resource
		go RefetchLogs()
	case MoveCursorAction:
		nextPos := Position{
			x: _state.Cursor.x + a.x,
			y: _state.Cursor.y + a.y,
		}
		_state.Cursor = ensureCursorInBounds(nextPos)
		_state.LogsUpdatedAt = time.Now().UTC()
	case SetCursorAction:
		_state.Cursor = ensureCursorInBounds(Position{x: a.x, y: a.y})
		_state.LogsUpdatedAt = time.Now().UTC()
	case SetErrorAction:
		_state.Flash = a.message
		_state.Status = ErrorStatus
	}
	return false
}

// EventLoop is the main entry point for the ui.
func EventLoop() {
	for {
		prevState := _state
		shouldShutdown := false
		action := <-dispatch
		shouldShutdown = handleAction(action)
		// We don't want to try to render more often than once per 20ms, or we
		// can run into race conditions with the terminal.  Keep handling
		// events until we haven't had one for 20ms, then draw.
		continueHandlingEvents := true
		for continueHandlingEvents {
			select {
			case action := <-dispatch:
				shouldShutdown = handleAction(action)
			case <-time.After(time.Millisecond * time.Duration(10)):
				Draw(prevState, GetState())
				continueHandlingEvents = false
			}
		}
		if shouldShutdown {
			break
		}
	}
}

func GetState() State {
	return _state
}
