#!/usr/bin/env bash

workers="${WEB_CONCURRENCY:-4}"
if [[ "$workers" == "0" ]]; then
	workers="$(python -c 'import multiprocessing; print(multiprocessing.cpu_count() * 2 + 1)')"
fi

exec uvicorn uploader.app:app \
	--host 0.0.0.0 \
	--port 80 \
	--workers "$workers" \
	--timeout-keep-alive "${WEB_KEEP_ALIVE:-30}" \
	--timeout-graceful-shutdown "${WEB_GRACEFUL_SHUTDOWN_TIMEOUT:-30}"
