# File Uploader

This project contains Flask based File Uploader.

## Versioning

Please use [bump.sh](./bump.sh) script to increase the version of the app. This
script will update version both in [pyproject.toml](./pyproject.toml) and
[app version](./uploader/_version.py) files.

:warning: If you don't want or unable to use this script it is important to
update [version](./pyproject.toml#L3) in [pyproject.toml](./pyproject.toml) file
as it is used when image is built to overwrite version in
[app version](./uploader/_version.py) file.

:warning: There is also
[git hooks](https://github.com/thomasthiebaud/poetry-githooks) to use with
poetry. You can enable them with `poetry run githooks setup`.

## Debugging

You can use [debug.sh](./debug.sh) to debug the app locally:

```bash
poetry run ./debug.sh
```

## Running in GNU/Linux

It is better to have Python and
[Poetry](https://python-poetry.org/docs/#installation) installed before. You can
use the following steps to run the app in GNU/Linux:

```bash
poetry build --format wheel
poetry export --format requirements.txt --output requirements.txt --without-hashes
pip install --no-cache-dir gunicorn[gevent]
pip install --no-cache-dir dist/uploader-*.whl -r requirements.txt
./entrypoint.sh --without-nginx
```

You can provide `UPLOAD_FOLDER` as an
[environment variable](#environment-variables) and bind to a different `port` in
[entrypoint](./entrypoint.sh) before starting.

Stopping it:

```bash
kill $(cat file_uploader.pid)
```

## Running in Windows

It is better to have Python and
[Poetry](https://python-poetry.org/docs/#installation) installed before. You can
use the following steps to run the app in Windows:

```bash
poetry build --format wheel
poetry export --format requirements.txt --output requirements.txt --without-hashes
pip install --no-cache-dir dist/uploader-*.whl -r requirements.txt
./start.sh
```

Please check `UPLOAD_FOLDER` and `port` in [start script](./start.sh) before
starting.

You can stop it by stopping with `CTRL+C` or by closing the terminal.

## Running as container

:warning: When checked out on Windows ensure that the line endings of scripts
are linux style **before** building the image.

The image containing the `File Uploader` service is built using
[Dockerfile](./Dockerfile).

You can use the following command to build and run the container.

Building the image:

```bash
docker build -t file-uploader .
```

Running the container:

```bash
docker run --name file-uploader -it --rm -p 80:80 file-uploader
```

All endpoints will be available at [localhost](http://localhost)

`File Uploader` code and logs are under `/app` folder in the container.

## Environment variables

Here is the list of environment variables that are used:

- `UPLOAD_FOLDER`: Path to the folder to store the uploaded files.
- [WEB_CONCURRENCY](https://docs.gunicorn.org/en/stable/settings.html#workers):
  The number of worker processes for handling requests.
- [WEB_TIMEOUT](https://docs.gunicorn.org/en/stable/settings.html#timeout):
  Workers silent for more than this many seconds are killed and restarted.
- [WEB_KEEP_ALIVE](https://docs.gunicorn.org/en/stable/settings.html#keepalive):
  The number of seconds to wait for requests on a Keep-Alive connection.

## Package management

We are using [poetry](https://python-poetry.org/) Python package and dependency
manager.

- Init interactively `poetry init`
- Add package `poetry add package-name`
- Remove package `poetry remove package-name`
- Install dependencies `poetry install`
- Update dependencies `poetry update`
- Show available packages `poetry show`
- Run a command in the virtualenv `poetry run command`
- Open virtualenv `poetry shell`
