SERVER_COUNT=1

source shutdown_servers.sh

pushd .. 2>&1 > /dev/null

rm locks/file*.lock

echo Starting interface server ...
docker run --rm -d --network wfpb --name glycosight-interface \
    --mount src=$(pwd)/tmp/,target=/flask/tmp,type=bind \
    --mount src=$(pwd)/locks/,target=/flask/locks,type=bind \
    glycosight-interface flask --app glycosight_interface.py run --port=5000 --host=0.0.0.0

for i in $(seq 1 $SERVER_COUNT); do
    if [[ ! -d "tmp/$i" ]]; then
        echo Did not find tmp folder $i - creating it
        mkdir -p "tmp/$i"
    else
        echo Found folder tmp/$i, proceeding
    fi
    if [[ ! -f "locks/file$i.lock" ]]; then
        echo Missing lock file $i - creating
        touch locks/file$i.lock
    else
        echo Found lock file $i, proceeding
    fi
    echo Starting backend server: $i
    docker run --rm -d --network wfpb --name glycosight-backend-$i \
        --mount src=$(pwd)/tmp/,target=/flask/tmp,type=bind \
        --mount src=$(pwd)/locks/,target=/flask/locks,type=bind \
        glycosight-backend flask --app glycosight_server.py run --port=500$i --host=0.0.0.0
done

popd 2>&1 > /dev/null
