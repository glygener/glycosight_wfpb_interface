#!/bin/bash

set -e

ID=$(id -gn)
if [[ $ID =~ pat ]]; then
    WFPB_BUILDER_PATH=~/gwu-src/playbook-partnership
else
    # Fill in the path to WFPB code here
    WFPB_BUILDER_PATH=""
fi

pushd ../../dockers/ui 2>&1 > /dev/null

docker build -t wfpb-ui-base -f dockerfile.wfpb.base .

popd 2>&1 > /dev/null