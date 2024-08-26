import os
import multiprocessing

# Start [gunicorn](https://gunicorn.org/)
# serving from port 80
bind = "0.0.0.0:80"

# at the /app folder
chdir = "/app"

# using [gevent](https://www.gevent.org/) worker
worker_class = "gevent"

# using 4 gevent workers as default
workers = int(os.environ.get("WEB_CONCURRENCY", 4))
if workers == 0:
    # if user provided 0 as the worker count
    # calculate gevent worker count according to CPU count
    workers = multiprocessing.cpu_count() * 2 + 1

# using 60 minutes worker timeout
timeout = int(os.environ.get("WEB_TIMEOUT", 600))

# using 30 seconds keep-alive waiting time
keepalive = int(os.environ.get("WEB_KEEP_ALIVE", 30))

# using log configuration in [log.conf](./log.conf) file
logconfig = "log.conf"

print(
    f"Starting gunicorn to serve Flask backend application as a daemon using {
        workers} {worker_class} workers"
)
