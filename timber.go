package main

//go:generate protoc --go_out=. ./logservice/pb/log_service.proto.txt

import (
	"flag"
	"io/ioutil"
	"log"
	"os"
	"os/user"
	"path"
	"sync"

	tui "github.com/gizak/termui"
	"google.golang.org/grpc/grpclog"

	"./logservice"
	"./ui"
)

var configFilename = ".timberrc"

func main() {
	// grpc spews annoying messages when the http2 connection times out, which
	// meses up the UI.  This suppresses those messages
	grpclog.SetLogger(log.New(ioutil.Discard, "", 0))
	user, userErr := user.Current()
	if userErr != nil {
		panic(userErr)
	}
	configFilename = path.Join(user.HomeDir, configFilename)

	proj := flag.String("project", "", "the google cloud project id")
	flag.Parse()

	project := *proj
	if project == "" {
		config, err := ioutil.ReadFile(configFilename)
		if err == nil {
			project = string(config)
		}
	} else {
		f, err := os.Create(configFilename)
		if err == nil {
			defer f.Close()
			f.WriteString(project)
		}
	}

	if project == "" {
		panic("Must supply a project id via -project or your ~/.timberrc file")
	}
	logservice.SetProject(project)

	err := tui.Init()
	if err != nil {
		panic(err)
	}
	defer tui.Close()
	ui.InstallEventHandlers()
	wg := sync.WaitGroup{}
	wg.Add(1)
	go func() {
		defer wg.Done()
		ui.EventLoop()
	}()
	go ui.RefetchLogs()
	wg.Add(1)
	go func() {
		defer wg.Done()
		tui.Loop()
	}()
	wg.Wait()
}
