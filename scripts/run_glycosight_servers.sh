SERVER_COUNT=1

pushd .. 2>&1 > /dev/null

echo Starting interface server ...


for i in $(seq 1 $SERVER_COUNT); do
    echo Starting backend server: $i
    docker run --rm -d --network wfpb --name wfpb-backend-$i --mount src=$(pwd)/tmp/,target=/data,type=bind wfpb:glycosight-backend flask --app glycosight_server.py run --port=500$i --host=0.0.0.0
done

popd 2>&1 > /dev/null
