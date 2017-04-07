#!/bin/bash

set -e

mkdir build

DEST_LINUX="gs://timber-dist/linux-x86_64/timber"
DEST_OSX="gs://timber-dist/osx/timber"

GOARCH=amd64 GOOS=linux go build -o build/timber-linux timber.go
gsutil cp build/timber-linux $DEST_LINUX
gsutil setmeta -h "Cache-Control:private, max-age=0, no-transform" $DEST_LINUX
gsutil acl ch -u AllUsers:R $DEST_LINUX

GOARCH=amd64 GOOS=darwin go build -o build/timber-osx timber.go
gsutil cp build/timber-osx $DEST_OSX
gsutil setmeta -h "Cache-Control:private, max-age=0, no-transform" $DEST_OSX
gsutil acl ch -u AllUsers:R $DEST_OSX

rm -r build
