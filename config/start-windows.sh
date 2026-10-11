#!/usr/bin/env bash
# Please note that double slash is important for path injection check
export UPLOAD_FOLDER="C:\\temp\\file-uploader"

# run app
uvicorn uploader.app:app --host=0.0.0.0 --port=80 --workers "${WEB_CONCURRENCY:-1}"