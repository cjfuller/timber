package ui

import (
	"fmt"
	_ "image"
	"sort"
	"strings"
)

// TODO(colin): maybe switch to a different lower-level library; there's a lot
// of flickering and the occastional panic during rendering with this one.
import tui "github.com/gizak/termui"

import "../logservice"

func LogsHeight() int {
	return tui.TermHeight() - 2
}

func LogsWidth() int {
	return tui.TermWidth()
}

func levelIndicator(level string) string {
	switch level {
	case "Default", "Debug":
		return white("λ")
	case "Info":
		return "[i](fg-blue)"
	case "Warning":
		return "[!](fg-yellow)"
	case "Error":
		return "[→](fg-red)"
	case "Critical":
		return "[▶](fg-magenta)"
	default:
		return " "
	}
}

func colorStatusCode(status string) string {
	if strings.HasPrefix(status, "4") {
		return fmt.Sprintf("[%s](fg-yellow)", status)
	} else if strings.HasPrefix(status, "5") {
		return fmt.Sprintf("[%s](fg-red)", status)
	}
	return white(status)
}

func white(msg string) string {
	return fmt.Sprintf("[%s](fg-white)", msg)
}

func module(mod string) string {
	if mod == "" {
		mod = "default"
	}
	return white(mod)
}

func drawStatusLine(str string) {
	text := tui.NewPar(str)
	text.Border = false
	text.Width = len(str)
	text.Height = 1
	text.Y = LogsHeight()
	tui.Render(text)
}

func drawCommandLine(str string, inCommandMode bool) {
	// tui.ClearArea(image.Rectangle{
	// 	Min: image.Point{X: 0, Y: LogsHeight() + 1},
	// 	Max: image.Point{X: len(str) + 1, Y: LogsHeight() + 2},
	// }, tui.ColorDefault)
	if inCommandMode {
		str = ":" + str
	}
	if len(str) < LogsWidth() {
		str += strings.Repeat(" ", LogsWidth()-len(str))
	}
	text := tui.NewPar(str)
	text.Border = false
	text.Width = len(str)
	text.Height = 1
	text.Y = LogsHeight() + 1
	tui.Render(text)
}

func shutdown() {
	Dispatch(ShutdownAction{})
	tui.StopLoop()
}

type eventHandler func(tui.Event)

func noOp(_ tui.Event) {
	return
}

func normalOnly(f eventHandler) eventHandler {
	return handleByMode(f, noOp, noOp)
}

func focusOnly(f eventHandler) eventHandler {
	return handleByMode(noOp, f, noOp)
}

func commandOnly(f eventHandler) eventHandler {
	return handleByMode(noOp, noOp, f)
}

func handleByMode(normalCallback eventHandler, focusCallback eventHandler, commandCallback eventHandler) eventHandler {
	return func(e tui.Event) {
		state := GetState()
		if state.Mode == NormalMode {
			normalCallback(e)
		} else if state.Mode == FocusMode {
			focusCallback(e)
		} else if state.Mode == CommandMode {
			commandCallback(e)
		}
	}
}

// InstallEventHandlers sets up the handlers for all keyboard events.
func InstallEventHandlers() {
	tui.Handle("/sys/kbd/q", handleByMode(
		func(_ tui.Event) { shutdown() },
		func(_ tui.Event) { Dispatch(SetInputModeAction{mode: NormalMode}) },
		func(_ tui.Event) { Dispatch(AppendToCommandAction{text: "q"}) },
	))
	tui.Handle("/sys/kbd/r", handleByMode(
		func(_ tui.Event) { go RefetchLogs() },
		noOp,
		func(_ tui.Event) { Dispatch(AppendToCommandAction{text: "r"}) },
	))
	tui.Handle("/sys/kbd/:", handleByMode(
		func(_ tui.Event) { Dispatch(SetInputModeAction{mode: "command"}) },
		noOp,
		func(_ tui.Event) { Dispatch(AppendToCommandAction{text: ":"}) },
	))
	tui.Handle("/sys/kbd/j", handleByMode(
		func(_ tui.Event) { Dispatch(MoveCursorAction{x: 0, y: 1}) },
		noOp,
		func(_ tui.Event) { Dispatch(AppendToCommandAction{text: "j"}) },
	))
	tui.Handle("/sys/kbd/k", handleByMode(
		func(_ tui.Event) { Dispatch(MoveCursorAction{x: 0, y: -1}) },
		noOp,
		func(_ tui.Event) { Dispatch(AppendToCommandAction{text: "k"}) },
	))
	tui.Handle("/sys/kbd/>", handleByMode(
		func(_ tui.Event) { Dispatch(SetInputModeAction{mode: "focus"}) },
		noOp,
		func(_ tui.Event) { Dispatch(AppendToCommandAction{text: ">"}) },
	))
	tui.Handle("/sys/kbd/C-c", func(_ tui.Event) {
		shutdown()
	})
	tui.Handle("/sys/kbd/<space>", func(_ tui.Event) {
		Dispatch(AppendToCommandAction{text: " "})
	})
	tui.Handle("/sys/kbd/C-8", func(_ tui.Event) {
		// This is backspace for me.  Might be different on other systems?
		Dispatch(BackspaceCommandAction{})
	})
	tui.Handle("/sys/kbd/<enter>", commandOnly(func(e tui.Event) {
		command := GetState().CommandBuffer
		Dispatch(ClearCommandAction{})
		Dispatch(ProcessCommandAction{command: command})
	}))
	tui.Handle("/sys/kbd", commandOnly(func(e tui.Event) {
		if evtKbd, ok := e.Data.(tui.EvtKbd); ok {
			Dispatch(AppendToCommandAction{text: evtKbd.KeyStr})
		}
	}))
}

func formatLog(log logservice.LogEntryMin) []string {
	return []string{
		levelIndicator(log.Severity),
		white(log.Timestamp.String()),
		white(log.Version),
		module(log.Module),
		colorStatusCode(log.Status),
		white(log.Method),
		white(log.Resource),
	}
}

func formatLogEntry(log logservice.LogLine) [][]string {
	// TODO(colin): implement better wrapping.
	messageLines := strings.Split(log.Message, "\n")
	formatted := make([][]string, 0, len(messageLines))
	for idx, line := range messageLines {
		severity := ""
		timestamp := ""
		if idx == 0 {
			severity = log.Severity
			timestamp = log.Timestamp.String()
		}
		lineArr := []string{
			levelIndicator(severity),
			white(timestamp),
			white(line),
		}
		formatted = append(formatted, lineArr)
	}
	return formatted
}

func setTableDefaults(table *tui.Table) {
	table.Separator = false
	table.Border = false
	table.FgColor = tui.ColorBlack
	table.BgColor = tui.ColorDefault
	table.TextAlign = tui.AlignLeft
	table.Analysis()
	table.SetSize()
}

func drawLogs(state State) {
	tui.Clear()
	logTable := tui.NewTable()
	rows := make([][]string, 0)
	for rowIdx, log := range state.Logs {
		// TODO(colin): eew, don't redraw all the logs every time the cursor moves
		cursor := ""
		if rowIdx == state.Cursor.y {
			cursor = "[▶](fg-cyan)"
		}
		rows = append(rows,
			append(
				[]string{cursor},
				formatLog(log)...,
			))
	}
	logTable.Rows = rows
	setTableDefaults(logTable)
	tui.Render(logTable)
}

func drawFocus(state State) {
	focusLog := state.Logs[state.Cursor.y]
	tui.Clear()
	headerTable := tui.NewTable()
	rows := [][]string{
		append(
			[]string{"[Detail for:](fg-white)"},
			formatLog(focusLog)...,
		),
	}
	headerTable.Rows = rows
	setTableDefaults(headerTable)
	tui.Render(headerTable)
	detailTable := tui.NewTable()
	detailTable.Y = 2
	rows = make([][]string, 0)
	if focusLog.Messages != nil {
		sort.Sort(focusLog.Messages)
		for _, entry := range focusLog.Messages {
			rows = append(rows, formatLogEntry(entry)...)
		}
	}
	detailTable.Rows = rows
	setTableDefaults(detailTable)
	tui.Render(detailTable)
}

func Draw(prevState State, state State) {
	shouldRedrawLogs := ((state.Mode == NormalMode && prevState.Mode != NormalMode) ||
		(state.Mode == NormalMode && state.Logs != nil && state.LogsUpdatedAt != prevState.LogsUpdatedAt))
	if shouldRedrawLogs {
		drawLogs(state)
	} else if state.Mode == FocusMode {
		drawFocus(state)
	}
	if state.Status == LoadingStatus && state.Mode != FocusMode {
		drawStatusLine("loading...")
	}
	if state.Status == ErrorStatus && state.Mode != FocusMode {
		drawStatusLine("[Error:](fg-red) " + state.Flash)
	}
	if state.Mode == CommandMode || prevState.CommandBuffer != state.CommandBuffer {
		drawCommandLine(state.CommandBuffer, state.Mode == CommandMode)
	}
}
