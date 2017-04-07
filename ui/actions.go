package ui

import "../logservice"

type ShutdownAction struct{}

type StoreLogsAction struct {
	logs []logservice.LogEntryMin
}

type MoveCursorAction struct {
	x int
	y int
}

type SetCursorAction struct {
	x int
	y int
}

type LoadingAction struct{}

type RenderAction struct{}

type SetViewAction struct {
	view string
}

type SetLogLevelAction struct {
	logLevel string
}

type SetInputModeAction struct {
	mode string
}

type AppendToCommandAction struct {
	text string
}

type BackspaceCommandAction struct{}

type ClearCommandAction struct{}

type ProcessCommandAction struct {
	command string
}

type SetResourceFilterAction struct {
	resource string
}

type SetVersionFilterAction struct {
	version string
}

type SetErrorAction struct {
	message string
}
