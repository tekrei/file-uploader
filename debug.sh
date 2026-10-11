#!/usr/bin/env bash
export UPLOAD_FOLDER=/tmp/file-uploader

# run app
uvicorn uploader.app:app --reload
