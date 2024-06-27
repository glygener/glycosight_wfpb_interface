#!/bin/bash

echo Shutting down glycosight servers

docker ps --filter name=glycosight* -aq | xargs docker stop
docker ps --filter name=glycosight* -aq | xargs docker rm

echo ...shutdown complete
