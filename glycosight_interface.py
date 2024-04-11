from flask import Flask, request, Response, send_from_directory, jsonify
from flask_cors import CORS, cross_origin

import os
import logging
import json

app = Flask(__name__)
cors = CORS(app)
app.config["CORS_HEADERS"] = "Content-Type"
app.config["DOWNLOAD_FOLDER"] = os.path.join(
    os.path.dirname(app.instance_path), "models"
)

app.logger.setLevel(logging.DEBUG)

@app.route("/ping", methods=["GET"])
def ping():
    try:
        req = request
        return Response("PONG\n")
    except Exception as e:
        app.logger.debug(f"---> Exception!!\n{e}")
        return Response(f"ERROR: {e}")

@app.route("/upload", methods=["POST"])
def upload():
    target = request.args.get("q", None)
    return jsonify({"results": "complete"})
