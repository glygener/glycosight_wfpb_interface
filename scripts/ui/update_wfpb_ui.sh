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
docker images | grep wfpb-ui-initial 2>&1 > /dev/null;
# Relies on exit > 0
if [[ $? != 0 ]]; then
    echo Didn\'t find the initial node+python dependencies docker, aborting
    echo Please run "build_wfpb_ui.sh"
else
    echo Found the requirements docker, proceeding
fi
echo ...Checked exit status!
set -e

pushd ../..  2>&1 > /dev/null

cp dockers/ui/dockerfile.ui $WFPB_BUILDER_PATH

cd $WFPB_BUILDER_PATH

git diff > ui.patch

# Relies on exit > 0
echo Building the UI
set +e
docker stop wfpb-ui
docker rmi wfpb-ui
set -e
docker build -t wfpb-ui -f dockerfile.ui .

rm dockerfile.ui ui.patch

popd 2>&1 > /dev/null
