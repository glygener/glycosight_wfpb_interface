#!/bin/bash

docker stop glycosight-interface
docker rm glycosight-interface

pushd .. 2>&1 > /dev/null

docker build -t glycosight-interface -f dockers/dockerfile.interface .

popd 2>&1 > /dev/null
