from flask import Flask, request, Response, send_from_directory, jsonify

import configparser
import gzip
import io
import logging
import os
import pandas as pd
import shutil
import time
import tarfile
import subprocess

config = configparser.ConfigParser()
config.read("./app.config")

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)

FLASK_MODE = config["mode"]["mode"]

BASE_PATH = (
    os.path.abspath(os.path.join(os.path.dirname(__file__)))
    if FLASK_MODE == "dev"
    else "/flask"
)

DATA_DIR = os.path.join(BASE_PATH, "tmp") if FLASK_MODE == "dev" else "/flask/tmp"
DOCKER_DIR = "/data" if FLASK_MODE == "dev" else None


def get_dir(dir_name=None):
    return f"{DATA_DIR}" if dir_name is None else f"{DATA_DIR}/{dir_name}"


def untar_file(dir, file):
    tar = tarfile.open(os.path.join(dir, file))
    tar.extractall(path=dir)
    tar.close()
    os.remove(os.path.join(dir, file))


def create_archive(file, dir, logger=None):
    file_full_path = os.path.join(dir, file)
    arc_path = dir
    gz_name = file + ".gz"
    if logger:
        logger.debug(f"\nFile: {file}\nArc Path: {arc_path}\ngz Name: {gz_name}")

    cwd = os.getcwd()
    os.chdir(arc_path)
    with open(file_full_path, "rb") as f_in:
        with gzip.open(gz_name, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

    os.chdir(cwd)
    os.remove(file_full_path)


def process_output(output_as_list, logger=None):
    while not output_as_list[0].startswith("UniProtAcc"):
        test = output_as_list.pop(0)
        if logger:
            logger.debug(f"===> Popped line {test}")
    return output_as_list


def process_input_files(dir_name):

    dir = get_dir(dir_name)

    for parent_dir, directories, files in os.walk(dir):
        if parent_dir != dir:
            continue
        file = [f for f in files if (f.endswith("gz") or f.endswith("mzid"))]
    if len(file) > 1:
        app.logger.debug(f"Too many files in {dir}: {files}")
        app.logger.debug("Aborting")
        return False

    file = file[0]
    if file.endswith("tar.gz") or file.endswith(".tgz"):
        untar_file(dir, file)
    elif file.endswith(".mzid"):
        app.logger.debug(f"===> Creating archive with file {file}; dir {dir} <===")
        create_archive(file, dir, app.logger)
        app.logger.debug("===> Archive created! <===")
    return True


def remove_input_files(dir):
    for file in os.listdir(dir):
        if file.endswith("gz"):
            os.remove(os.path.join(dir, file))


if FLASK_MODE == "dev":
    app.logger.debug("Found DEVELOPMENT environment")
    import docker

    client = docker.from_env()

    user_string = f"{os.geteuid()}:{os.getegid()}"

    def run_analysis(dir_name=None, logger=None):

        if not process_input_files(dir_name):
            return io.String("Error\tAborting")

        dir = get_dir(dir_name)

        arg = "" if dir_name is None else f"{dir_name}/"
        glycosight_command = (
            f'/GlycoSight/bin/nlinkedsites.sh "{DOCKER_DIR}/*.gz"'
            if dir_name is None
            else f'/GlycoSight/bin/nlinkedsites.sh "{DOCKER_DIR}/{dir_name}/*.gz"'
        )

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
                    "\n".join(
                        process_output(
                            container.logs().decode("utf-8").split("\n"), app.logger
                        )
                    )
                )
                container.remove()

        if not remove_input_files(dir):
            # Error handling?
            ...

        return output

else:
    app.logger.debug("Found FLASK environment")

    def run_analysis(dir_name=None, logger=None):

        SUB_DIR = "" if dir_name is None else f"/{dir_name}"

        target_dir = "{}{}".format(DATA_DIR, SUB_DIR)
        target_files = target_dir + "/*.gz"

        if not process_input_files(dir_name):
            return io.String("Error\tAborting")

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
            # Error handling. Note that GlycoSight uses stderr for some logging
            #   to avoid polluting the stdout stream (with results)
            # app.logger.error(f"ERROR: stderr is {completed_process.stderr}")
            # app.logger.error(
            #     f"ERROR: Return code was {completed_process.check_returncode()}"
            # )
            ...

        # Blow up the files
        dir = get_dir(dir_name)
        if not remove_input_files(dir):
            # Error handling?
            ...

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
