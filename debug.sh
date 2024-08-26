#!/usr/bin/env bash
export FLASK_ENV=development
export FLASK_APP=uploader.app
export UPLOAD_FOLDER=/tmp/file-uploader

# run app
flask run
