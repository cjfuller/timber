#!/bin/bash

set -e

mkdir build

GOARCH=amd64 GOOS=linux go build -o build/timber-linux timber.go
gsutil cp build/timber-linux gs://timber-dist/linux-x86_64/timber

GOARCH=amd64 GOOS=darwin go build -o build/timber-osx timber.go
gsutil cp build/timber-osx gs://timber-dist/osx/timber

rm -r build
