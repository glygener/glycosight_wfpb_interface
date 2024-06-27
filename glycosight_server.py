from flask import Flask, request, Response, send_from_directory, jsonify

import configparser
import io
import logging
import os
import pandas as pd
import time
import subprocess

BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__)))
DATA_DIR = os.path.join(BASE_PATH, "tmp")

config = configparser.ConfigParser()
config.read(os.path.join(BASE_PATH, "./app.config"))

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)

FLASK_MODE = config["mode"]["mode"]

if FLASK_MODE == "dev":
    app.logger.debug("Found DEVELOPMENT environment")
    import docker

    client = docker.from_env()

    glycosight_command = '/GlycoSight/bin/nlinkedsites.sh "*.gz"'
    user_string = f"{os.geteuid()}:{os.getegid()}"

    def run_analysis(dir_name=None):
        app.logger.debug("*" * 40)
        app.logger.debug("\t\tRUNNING ANALYSIS")
        app.logger.debug("*" * 40)
        container = client.containers.run(
            "glyomics/glycosight:1.1.0",
            detach=True,
            volumes={DATA_DIR: {"bind": "/data/", "mode": "rw"}},
            command=glycosight_command,
            user=user_string,
        )

        counter = 0
        while container.status != "exited" and counter < 20:
            container.reload()
            if container.status == "exited":
                output = io.StringIO(
                    "\n".join(container.logs().decode("utf-8").split("\n")[2:])
                )
                container.remove()
                return output

else:
    app.logger.debug("Found FLASK environment")

    def run_analysis(dir_name=None, logger=None):

        SUB_DIR = "" if dir_name is None else f"/{dir_name}"

        target_dir = '"{}{}"'.format(DATA_DIR, SUB_DIR)
        target_files = target_dir + "/*.gz"

        glycosight_command = [
            "/GlycoSight/bin/nlinkedsites.sh",
            target_files,
        ]
        if logger is not None:
            logger.debug(f"===> Running command {glycosight_command}")
        timeout = 3600  # 1 hour for a run
        start = time.time()
        completed_process = subprocess.run(
            glycosight_command, capture_output=True, timeout=timeout, text=True
        )
        # Error handling
        if completed_process.stderr or completed_process.check_returncode():
            # Do something?
            ...

        # Blow up the files
        for f in os.listdir(target_dir):
            if f.endswith("gz"):
                os.remove(f)

        return io.StringIO(completed_process.stdout)


@app.route("/ping")
def ping():
    return "PONG\n"


@app.route("/perform-analysis")
def glycosight_analysis():

    directory_name = request.args.get("q", None)

    # Format the output for display
    start = time.time()
    try:
        glycosight_results = run_analysis(directory_name, app.logger)
        output_df = pd.read_table(glycosight_results)
        output = output_df.to_dict(orient="records")
    except Exception as e:
        app.logger.critical(f"Exception:\n{e}")
    app.logger.debug(f"...Analysis complete. Required {time.time() - start:.1f} s")
    return jsonify({"results": output})

    # output = "\n".join(container.logs().decode("utf-8").split("\n")[2:])
    # container.remove()

    # print(f"Output:\n{'*'*80}\n{output}\n{'*'*80}")
