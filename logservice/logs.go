package logservice

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"./pb"
	"cloud.google.com/go/logging"
	"cloud.google.com/go/logging/logadmin"
)

type LogServiceConfig struct {
	LogLevel string
	Resource string
	Version  string
}

type LogLine struct {
	Message   string
	Severity  string
	Timestamp time.Time
}

type LogEntryMin struct {
	IP        string
	Latency   string
	Messages  LogLineSlice
	Method    string
	Module    string
	RequestID string
	Resource  string
	Severity  string
	Status    string
	Timestamp time.Time
	UserAgent string
	Version   string
}

type LogLineSlice []LogLine

func (self LogLineSlice) Len() int {
	return len(self)
}

func (self LogLineSlice) Less(i int, j int) bool {
	if self[i].Timestamp.Before(self[j].Timestamp) {
		return true
	}
	return false
}

func (self LogLineSlice) Swap(i int, j int) {
	temp := self[i]
	self[i] = self[j]
	self[j] = temp
}

func convertTime(ts pb.Timestamp) time.Time {
	var seconds int64
	var nanos int64
	if ts.Seconds != nil {
		seconds = *ts.Seconds
	}
	if ts.Nanos != nil {
		nanos = int64(*ts.Nanos)
	}
	return time.Unix(seconds, nanos).UTC()
}

func convertDuration(ts pb.Latency) time.Duration {
	var seconds int64
	var nanos int64
	if ts.Seconds != nil {
		seconds = *ts.Seconds
	}
	if ts.Nanos != nil {
		nanos = int64(*ts.Nanos)
	}
	return time.Duration(seconds)*time.Second + time.Duration(nanos)*time.Nanosecond
}

func elvis(item *string, defaultValue string) string {
	if item != nil {
		return *item
	}
	return defaultValue
}

func formatEntry(e *logging.Entry) (LogEntryMin, error) {
	payload, ok := e.Payload.(*pb.RequestLog)
	if ok {
		messages := make([]LogLine, 0)
		lines := payload.Line
		if lines != nil {
			for _, line := range lines {
				messages = append(messages, LogLine{
					Message:   elvis(line.LogMessage, ""),
					Severity:  logging.Severity(*line.Level).String(),
					Timestamp: convertTime(*line.Time),
				})
			}
		}
		status := 0
		if payload.Status != nil {
			status = int(*payload.Status)
		}
		return LogEntryMin{
			Timestamp: e.Timestamp,
			Severity:  e.Severity.String(),
			Messages:  messages,
			IP:        elvis(payload.Ip, ""),
			Latency:   fmt.Sprintf("%0.3f", convertDuration(*payload.Latency).Seconds()),
			Method:    elvis(payload.Method, ""),
			Module:    elvis(payload.ModuleId, ""),
			RequestID: elvis(payload.RequestId, ""),
			Resource:  elvis(payload.Resource, ""),
			Status:    fmt.Sprintf("%d", status),
			UserAgent: elvis(payload.UserAgent, ""),
			Version:   elvis(payload.VersionId, ""),
		}, nil
	}
	return LogEntryMin{}, errors.New("unable to format log entry")
}

var allowedLogLevels = map[string]bool{
	"DEFAULT":  true,
	"INFO":     true,
	"WARNING":  true,
	"ERROR":    true,
	"CRITICAL": true,
}

var project = ""

func SetProject(proj string) {
	project = proj
}

func FetchLatestLogs(n int, config LogServiceConfig) ([]LogEntryMin, error) {
	ctx := context.Background()
	client, err := logadmin.NewClient(ctx, project)
	if err != nil {
		return nil, err
	}
	logLevel := strings.ToUpper(config.LogLevel)
	_, validLevel := allowedLogLevels[logLevel]
	if !validLevel {
		// TODO(colin): message about this.
		logLevel = "ERROR"
	}
	filter := fmt.Sprintf("logName=projects/%s/logs/appengine.googleapis.com%%2Frequest_log", project)
	if logLevel != "DEFAULT" {
		filter += fmt.Sprintf(" severity>=%s", logLevel)
	}
	resource := config.Resource
	if resource != "" {
		filter += fmt.Sprintf(" protoPayload.resource:%s", resource)
	}
	entriesIter := client.Entries(ctx, logadmin.Filter(filter), logadmin.NewestFirst())
	entries := make([]LogEntryMin, 0, n)
	for i := 0; i < n; i++ {
		e, err := entriesIter.Next()
		if err != nil {
			return nil, err
		}
		formatted, formatErr := formatEntry(e)
		if formatErr == nil {
			entries = append(entries, formatted)
		}
	}
	return entries, nil
}
