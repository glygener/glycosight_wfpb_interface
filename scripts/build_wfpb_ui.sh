#!/bin/bash

set -e

ID=$(id -gn)
if [[ $ID =~ pat ]]; then
    WFPB_BUILDER_PATH=~/gwu-src/playbook-partnership
else
    # Fill in the path to WFPB code here
    WFPB_BUILDER_PATH=""
fi

echo Found $WFPB_BUILDER_PATH

if [ -z "$WFPB_BUILDER_PATH" ]; then
    echo No path to WFPB found, exiting \(Found $WFPB_BUILDER_PATH\)
    exit 1
fi
echo Proceeding ....

set +e
docker images | grep wfpb-ui-base 2>&1 > /dev/null;
# Relies on exit > 0
if [[ $? != 0 ]]; then
    echo Didn\'t find the base docker, building
    docker build -t wfpb-ui-base -f dockerfile.wfpb.base .
    if [[ $? != 0 ]]; then
        echo Docker build appears to have failed. Exiting...
        exit 2
    fi
else
    echo Found the base docker, proceeding
fi
echo ...Checked exit status!
set -e

cp dockerfile.wfpb.ui wfpb_requirements.txt $WFPB_BUILDER_PATH
pushd $WFPB_BUILDER_PATH 2>&1 > /dev/null

# Relies on exit > 0
echo Building the UI
set +e
docker stop wfpb-ui
docker rmi wfpb-ui
set -e
docker build -t wfpb-ui -f dockerfile.wfpb.ui .

rm dockerfile.wfpb.ui wfpb_requirements.txt
popd 2>&1 > /dev/null
