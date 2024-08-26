ARG PYTHON_VERSION=3.12-slim
FROM python:${PYTHON_VERSION} AS build

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_HOME="/opt/poetry"

RUN apt-get update && apt-get install -y --no-install-recommends curl

# Install poetry
RUN curl -sSL https://install.python-poetry.org | python -
ENV PATH="$POETRY_HOME/bin:$PATH"

WORKDIR /app

COPY pyproject.toml poetry.lock README.md ./
COPY ./uploader ./uploader

# Build app
RUN echo "__version__ = \"$(poetry version --short)\"" >uploader/_version.py \
    && poetry build --format wheel \
    && poetry export --format requirements.txt --output requirements.txt --without-hashes

FROM python:${PYTHON_VERSION}

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash curl htop iputils-ping jq nano netcat-traditional wget \
    && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ./config/log.conf ./config/gunicorn.conf.py ./config/entrypoint.sh ./

COPY --from=build /app/dist/uploader-*.whl /app/requirements.txt ./

RUN pip install --no-cache-dir gunicorn[gevent] \
    && pip install --no-cache-dir uploader-*.whl -r requirements.txt \
    && rm *.whl *.txt

RUN chmod +x entrypoint.sh

HEALTHCHECK CMD curl --fail http://localhost || exit 1

ENTRYPOINT ["./entrypoint.sh"]
