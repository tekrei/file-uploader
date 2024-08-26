#!/usr/bin/env bash

export UPLOAD_FOLDER=/tmp/file-uploader-test

coverage run -m unittest discover
coverage report -m
