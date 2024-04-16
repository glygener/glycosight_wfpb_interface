from flask import Flask, request, Response, send_from_directory, jsonify
from flask_cors import CORS, cross_origin

# NB Migrate to celery if we need to implement rate limits to
# e.g. N-threads on an M > N threaded machine
# See SO: https://stackoverflow.com/a/31867108
# import Celery
import base64
import configparser
import fcntl
import json
import logging
import os
import requests
import time

from hashlib import md5

BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__)))
WORK_DIR = os.path.join(BASE_PATH, "./tmp")
LOCK_DIR = os.path.join(BASE_PATH, "./locks")

# valid_lock_files = ["file1.lock", "file2.lock", "file3.lock"]
valid_lock_files = ["file1.lock"]

app = Flask(__name__)
cors = CORS(app, resources={r"/api/*": {"origins": ["http://localhost"]}})
app.config["CORS_HEADERS"] = ["Content-Type", "Access-Control-Allow-Origin"]
app.config["DOWNLOAD_FOLDER"] = os.path.join(
    os.path.dirname(app.instance_path), "models"
)

app.logger.setLevel(logging.DEBUG)

config = configparser.ConfigParser()
config.read(os.path.join(BASE_PATH, "./.env"))

FLASK_MODE = config["mode"]["mode"]
ANALYSIS_BACKEND = config[FLASK_MODE]["BackendBaseURL"]
ANALYSIS_PORT_BASE = int(config[FLASK_MODE]["BasePort"])
SHIM = (
    True
    if "Shim" in config[FLASK_MODE] and config[FLASK_MODE].getboolean("Shim")
    else False
)

ANALYSIS_URL = ANALYSIS_BACKEND + ":{}"


class LockManager:
    def __init__(self):
        self.lockedfiles = {}

    def acquire_lock(self):
        for lockname in valid_lock_files:
            # Acquire locks
            lock_path = os.path.join(LOCK_DIR, lockname)
            try:
                fd = open(lock_path)
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.lockedfiles[lockname] = fd
                return lockname
            except Exception as e:
                # app.logger.debug(f"Exception {e} on {lockname}. Trying next file")
                continue
        return False

    def release_lock(self, lockname):
        fd = self.lockedfiles[lockname]
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except:
            raise


lock_manager = LockManager()


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

    counter = 0
    start = time.time()
    app.logger.debug("...Analysis launched")

    # Block response until lock is acquired
    lockname = lock_manager.acquire_lock()
    while not lockname:
        time.sleep(1)
        app.logger.debug("---> Did not get a lock. Trying again ...")
        lockname = lock_manager.acquire_lock()
    # Launch analysis in Flask docker

    analysis_target = (
        ANALYSIS_URL.format(
            ANALYSIS_PORT_BASE + int(lockname.split(".")[0].lstrip("file"))
        )
        + "/perform-analysis"
    )
    app.logger.debug(f"Targeting analysis on port {analysis_target}")

    # Get response and return
    if SHIM:
        app.logger.debug("Sleeping 10 seconds while pretending to work")
        time.sleep(10)
        lock_manager.release_lock(lockname)
        return jsonify({"results": "complete"})
    app.logger.debug("Sending analysis request downstream")
    try:
        response = requests.get(analysis_target)
        if response.status_code != 200:
            lock_manager.release_lock(lockname)
            return jsonify({"errror": response.status_code})
    except:
        raise
    lock_manager.release_lock(lockname)
    return jsonify(json.loads((response.content.decode("utf-8"))))
