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
WORK_DIR = os.path.join(BASE_PATH, "tmp")
LOCK_DIR = os.path.join(BASE_PATH, "locks")

app = Flask(__name__)
cors = CORS(app, resources={r"/api/*": {
    "origins": ["http://localhost", "https://aws.glygen.org"]}
    })
app.config["CORS_HEADERS"] = ["Content-Type", "Access-Control-Allow-Origin"]
app.config["DOWNLOAD_FOLDER"] = os.path.join(
    os.path.dirname(app.instance_path), "models"
)

app.logger.setLevel(logging.DEBUG)

# valid_lock_files = ["file1.lock", "file2.lock", "file3.lock"]
valid_lock_files = []
for f in os.listdir("./locks"):
    if f.startswith("file"):
        valid_lock_files.append(f)

app.logger.debug(f"Found lock files: {valid_lock_files}")


config = configparser.ConfigParser()
config.read(os.path.join(BASE_PATH, "./app.config"))

FLASK_MODE = config["mode"]["mode"]
ANALYSIS_BACKEND = config[FLASK_MODE]["BackendBaseURL"]
ANALYSIS_PORT_BASE = int(config[FLASK_MODE]["BasePort"])
DRS_FILE_STORE_URL = config[FLASK_MODE]["WFPBInterfaceURL"]

SHIM = (
    True
    if "Shim" in config[FLASK_MODE] and config[FLASK_MODE].getboolean("Shim")
    else False
)
if FLASK_MODE == "dev":
    ANALYSIS_URL = ANALYSIS_BACKEND + ":{}"
    SINGLE_BACKEND = True
else:
    ANALYSIS_URL = ANALYSIS_BACKEND + "-{}:{}"
    SINGLE_BACKEND = False

############################### HELPERS ############################


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
                app.logger.debug(f"Exception {e} on {lockname}. Trying next file")
                continue
        return False

    def release_lock(self, lockname):
        fd = self.lockedfiles[lockname]
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except:
            raise


lock_manager = LockManager()


def run_analysis(lockname=None):

    session_timer = 20
    refresh_interval = 0.5

    counter = 0
    start = time.time()
    app.logger.debug("...Analysis launched")

    # Block response until lock is acquired
    if lockname is None:
        shim_interface = True
        lockname = lock_manager.acquire_lock()
        while not lockname:
            time.sleep(1)
            app.logger.debug("---> Did not get a lock. Trying again ...")
            lockname = lock_manager.acquire_lock()
            counter += 1
            if counter > session_timer:
                app.logger.debug("Session timeout error")
                return {"error": "No compute available, try again later"}
    else:
        shim_interface = False

    # Launch analysis in Flask docker

    lock_number = lockname.split(".")[0].lstrip("file")
    if not SINGLE_BACKEND:
        analysis_target = (
            ANALYSIS_URL.format(lock_number, ANALYSIS_PORT_BASE + int(lock_number))
            + f"/perform-analysis"
        )
    else:
        analysis_target = (
            ANALYSIS_URL.format(ANALYSIS_PORT_BASE + int(lock_number))
            + f"/perform-analysis"
        )

    if not shim_interface:
        analysis_target += f"?q={lock_number}"

    app.logger.debug(f"Targeting analysis on address target {analysis_target}")

    # Get response and return
    if SHIM:
        app.logger.debug("Sleeping 10 seconds while pretending to work")
        time.sleep(10)
        lock_manager.release_lock(lockname)
        return {"results": "complete"}
    app.logger.debug("Sending analysis request downstream")
    try:
        response = requests.get(
            analysis_target, headers={"Access-Control-Allow-Origin": "*"}
        )
        if response.status_code != 200:
            lock_manager.release_lock(lockname)
            return {"error": response.status_code}
        lock_manager.release_lock(lockname)
        return json.loads((response.content.decode("utf-8")))
    except:
        lock_manager.release_lock(lockname)
        raise


DUMMY_DATA = {
    "UniProtAcc": ["This", "is", "a", "test"],
    "AAPosition": [1, 2, 3],
    "SpectralCount": [4, 5, 6],
    "DistinctPeptideCount": [7, 8, 9],
    "Peptides": ["sample", "peptide", "strings"],
}

####################################################################


@app.route("/ping", methods=["GET"])
def ping():
    try:
        req = request
        return Response("PONG\n")
    except Exception as e:
        app.logger.debug(f"---> Exception!!\n{e}")
        return Response(f"ERROR: {e}")


@app.route("/api/upload-and-analyze", methods=["POST"])
@cross_origin("Access-Control-Allow-Origin")
def upload_and_analyze():
    target = request.args.get("q", None)
    file_name = request.args.get("n", None)
    app.logger.debug(f"Got request! Target URL was {target}. Filename was {file_name}")
    if target.startswith("drs"):
        locator = target.rsplit("/")[-1]
        app.logger.debug(f"Found URI locator {locator}")
        resourceURI = (
            f"{DRS_FILE_STORE_URL}/ga4gh/drs/v1/objects/{locator}/access/https/data"
        )
        app.logger.debug(f"---> Targeting URI {resourceURI}")
        response = requests.request("GET", resourceURI)
        if response.status_code != 200:
            # Error handling?
            app.logger.debug("===> ERROR NOTED <===")
            return jsonify(DUMMY_DATA)

    else:
        raise Exception("Engaging self destruct ... NOW")

    # Block response until lock is acquired
    counter = 0
    session_timer = 20

    lockname = lock_manager.acquire_lock()
    while not lockname:
        time.sleep(1)
        app.logger.debug("---> Did not get a lock. Trying again ...")
        lockname = lock_manager.acquire_lock()
        counter += 1
        if counter > session_timer:
            app.logger.debug("Session timeout error")
            return {"error": "No compute available, try again later"}

    # Write data to disk
    start = time.time()
    data = response.content
    file_hash = md5(data).hexdigest()
    duration = time.time() - start
    app.logger.debug(
        f"\n====== DATA\n\t-- Length {len(data)}\n\t-- Hash: {file_hash}\n\t-- Time needed: {duration * 1000:.1f} ms\n========="
    )
    lock_number = lockname.split(".")[0].lstrip("file")
    with open(os.path.join(WORK_DIR, lock_number, file_name), "wb") as fp:
        fp.write(data)
    fp.close()

    # Launch analysis
    result = run_analysis(lockname=lockname)
    return jsonify(result)


@app.route("/api/standalone-upload", methods=["POST"])
@cross_origin("Access-Control-Allow-Origin")
def standalone_upload():
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


@app.route("/api/test-access", methods=["POST"])
@cross_origin("Access-Control-Allow-Origin")
def test_access():
    target = request.args.get("q", None)
    app.logger.debug(f"Got TEST request! Target URL: {target}")
    return jsonify(DUMMY_DATA)


@app.route("/api/standalone-analyze")
@cross_origin("Access-Control-Allow-Origin")
def standalone_analyze():

    result = run_analysis()

    return jsonify(result)
