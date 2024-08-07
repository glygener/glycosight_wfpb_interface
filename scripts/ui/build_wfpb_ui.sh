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
    echo Didn\'t find the base docker, aborting
    echo Please run "build_base.sh"
else
    echo Found the base docker, proceeding
fi
echo ...Checked exit status!
docker rmi wfpb-ui-initial
set -e

pushd ../..  2>&1 > /dev/null

cp dockers/ui/dockerfile.ui.base dockers/ui/wfpb_requirements.txt $WFPB_BUILDER_PATH

cd $WFPB_BUILDER_PATH
git stash

# Relies on exit > 0
echo Building the UI

docker build -t wfpb-ui-initial -f dockerfile.ui.base .

git stash pop
rm dockerfile.ui.base wfpb_requirements.txt

popd 2>&1 > /dev/null
