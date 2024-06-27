#!/bin/bash

docker ps --filter name=glycosight-backend* -aq | xargs docker stop
docker ps --filter name=glycosight-backend* -aq | xargs docker rm

pushd ../ 2>&1 > /dev/null

docker build -t glycosight-backend -f dockers/dockerfile.backend .

popd 2>&1 > /dev/null
