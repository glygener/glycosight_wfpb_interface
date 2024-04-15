from flask import Flask, request, Response, send_from_directory, jsonify
from flask_cors import CORS, cross_origin

# NB Migrate to celery if we need to implement rate limits to
# e.g. N-threads on an M > N threaded machine
# See SO: https://stackoverflow.com/a/31867108
# import Celery
import base64
import docker
import json
import logging
import os
import pandas as pd
import time

from hashlib import md5
from io import StringIO

WORK_DIR = os.path.abspath("./tmp")

app = Flask(__name__)
cors = CORS(app, resources={r"/api/*": {"origins": ["http://localhost"]}})
app.config["CORS_HEADERS"] = ["Content-Type", "Access-Control-Allow-Origin"]
app.config["DOWNLOAD_FOLDER"] = os.path.join(
    os.path.dirname(app.instance_path), "models"
)

app.logger.setLevel(logging.DEBUG)

user_string = f"{os.geteuid()}:{os.getegid()}"
client = docker.from_env()
glycosight_command = '/GlycoSight/bin/nlinkedsites.sh "*.gz"'


@app.route("/ping", methods=["GET"])
def ping():
    try:
        req = request
        return Response("PONG\n")
    except Exception as e:
        app.logger.debug(f"---> Exception!!\n{e}")
        return Response(f"ERROR: {e}")


@app.route("/api/upload", methods=["POST"])
@cross_origin("Access-Control-Allow-Origin")
def upload():
    target = request.args.get("q", None)
    file_name = request.args.get("n", None)
    app.logger.debug(f"Got request! Target was {target}, filename was {file_name}")
    start = time.time()
    data = request.data.decode("utf-8").split(",")[1]
    file_hash = md5(data.encode("utf-8")).hexdigest()
    duration = time.time() - start
    app.logger.debug(
        f"\n====== DATA\n\t-- Length {len(data)}\n\t-- Hash: {file_hash}\n\t-- Time needed: {duration * 1000:.1f} ms\n========="
    )
    with open(os.path.join(WORK_DIR, file_name), "wb") as fp:
        fp.write(base64.b64decode(data.encode("utf-8")))
    fp.close()
    return jsonify({"results": "complete"})


@app.route("/api/analyze")
@cross_origin("Access-Control-Allow-Origin")
def analyze():

    session_timer = 20
    refresh_interval = 0.5

    container = client.containers.run(
        "glyomics/glycosight:1.1.0",
        detach=True,
        volumes={WORK_DIR: {"bind": "/data/", "mode": "rw"}},
        command=glycosight_command,
        user=user_string,
    )

    counter = 0
    start = time.time()
    app.logger.debug("...Analysis launched")

    while container.status != "exited":
        time.sleep(1)
        container.reload()
        if counter > int(session_timer / refresh_interval):
            container.kill()
            container.remove()
            # TODO Error handling
            return jsonify({"error": "Timeout reached"})
    analysis_output = StringIO(
        "\n".join(container.logs().decode("utf-8").split("\n")[2:])
    )
    container.remove()
    # Format the output for display
    output_df = pd.read_table(analysis_output)
    output = output_df.to_dict(orient="records")
    app.logger.debug(f"...Analysis complete. Required {time.time() - start:.1f} s")
    return jsonify({"results": output})
