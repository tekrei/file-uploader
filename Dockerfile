FROM ghcr.io/astral-sh/uv:python3.12-bookworm AS build

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./

RUN uv export --format requirements-txt --output-file requirements.txt \
    --no-editable --no-dev --no-emit-workspace --frozen --no-index --no-hashes

COPY ./uploader ./uploader

RUN uv build --wheel

FROM python:3.12-slim

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
