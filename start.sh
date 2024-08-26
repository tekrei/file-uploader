#!/usr/bin/env bash
export FLASK_APP=uploader.app
# Please note that double slash is important for path injection check
export UPLOAD_FOLDER="C:\\temp\\file-uploader"

# run app
flask run --host=0.0.0.0 --port=80
