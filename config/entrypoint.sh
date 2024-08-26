#!/usr/bin/env bash

# Create logs folder
mkdir /app/logs/

# Start gunicorn using default [gunicorn.conf.py](./config/gunicorn.conf.py) configuration file
gunicorn uploader.app:app
