from flask import Flask, request, Response, send_from_directory, jsonify

import configparser
import io
import logging
import os
import pandas as pd
import time
import subprocess

BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__)))
DATA_DIR = os.path.join(BASE_PATH, "./tmp")

config = configparser.ConfigParser()
config.read(os.path.join(BASE_PATH, "./.env"))

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)

FLASK_MODE = config["mode"]["mode"]

if FLASK_MODE == "dev":
    app.logger.debug("Found DEVELOPMENT environment")
    import docker

    client = docker.from_env()

    glycosight_command = '/GlycoSight/bin/nlinkedsites.sh "*.gz"'
    user_string = f"{os.geteuid()}:{os.getegid()}"

    def run_analysis():
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

    def run_analysis():
        glycosight_command = [
            "/GlycoSight/bin/nlinkedsites.sh",
            '"{}/*.gz"'.format(DATA_DIR),
        ]
        timeout = 3600  # 1 hour for a run
        start = time.time()
        completed_process = subprocess.run(
            glycosight_command, capture_output=True, timeout=timeout, text=True
        )
        # Error handling
        if completed_process.stderr or completed_process.check_returncode():
            # Do something?
            ...

        return completed_process.stdout


@app.route("/perform-analysis")
def glycosight_analysis():

    # Format the output for display
    start = time.time()
    glycosight_results = run_analysis()
    output_df = pd.read_table(glycosight_results)
    output = output_df.to_dict(orient="records")
    app.logger.debug(f"...Analysis complete. Required {time.time() - start:.1f} s")
    return jsonify({"results": output})

    # output = "\n".join(container.logs().decode("utf-8").split("\n")[2:])
    # container.remove()

    # print(f"Output:\n{'*'*80}\n{output}\n{'*'*80}")
