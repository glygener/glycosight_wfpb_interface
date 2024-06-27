#!/bin/bash

source shutdown_servers.sh

pushd .. 2>&1 > /dev/null
docker rmi glycosight-backend-base
docker rmi glycosight-interface-base

docker build -t glycosight-backend-base -f dockers/dockerfile.backend.base .
docker build -t glycosight-interface-base -f dockers/dockerfile.interface.base .

popd 2>&1 > /dev/null
