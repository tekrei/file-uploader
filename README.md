# File Uploader

This project contains a FastAPI-based file uploader.

## Debugging

You can use [debug.sh](./debug.sh) to debug the app locally:

```bash
uv run ./debug.sh
```

## Testing

Run the test suite and generate a coverage report from the repository root:

```bash
uv run --group dev bash ./test.sh
```

## Running from source

Requires Python 3.12 or later and [uv](https://docs.astral.sh/uv/getting-started/).

Build and install the app:

```bash
uv build --wheel
uv export --format requirements-txt --output-file requirements.txt --no-editable --no-dev --no-emit-workspace --frozen --no-index --no-hashes
pip install --no-cache-dir dist/uploader-*.whl -r requirements.txt
```

On GNU/Linux, start the server with:

```bash
./config/entrypoint.sh
```

On Windows, use a Bash shell. Review `UPLOAD_FOLDER` and the port in
[start-windows.sh](./config/start-windows.sh), then run:

```bash
./config/start-windows.sh
```

Stop the foreground server with `Ctrl+C`.

## Network security

This service has no authentication or authorization, and its CORS policy allows
all origins. It is intended only for trusted microservices on a private network.
Do not expose it directly to the internet or publish its port on a public host.

Recommended deployment options:

- **Docker:** Attach the uploader and its client services to an internal Docker
  network. Do not use `-p`/`--publish` for the uploader.
- **Kubernetes:** Use a `ClusterIP` Service and a `NetworkPolicy` that permits
  only the required client pods. Do not use a public Ingress, `NodePort`, or
  `LoadBalancer` Service.
- **Internal gateway:** If a gateway is required, keep it private and restrict
  access to trusted callers. The gateway does not replace network isolation.

## Authorization options

Authorization is not implemented by this service. Choose one of these options
before allowing clients to call it:

- **OAuth2 client credentials with JWTs (recommended):** Validate token
  signature, issuer, audience, and expiry. Require scopes such as `files:read`,
  `files:write`, and `files:delete` on the corresponding endpoints. Validation
  can live in the service or a trusted internal gateway.
- **Mutual TLS (mTLS):** Authenticate each calling service by its client
  certificate, preferably through a service mesh or internal proxy. Restrict
  which service identities can upload, read, or delete files.
- **API keys (simpler deployments):** Issue a separate key per client, send it
  in an authorization header, store it in a secret manager, and support
  rotation and revocation. Do not put keys in URLs; use network restrictions
  and rate limits as additional controls.

Network isolation is defense in depth, not a substitute for authorization.

## Running as container

:warning: When checked out on Windows ensure that the line endings of scripts
are linux style **before** building the image.

The image containing the `File Uploader` service is built using
[Dockerfile](./Dockerfile).

Build the image:

```bash
docker build -t file-uploader .
```

Create a private network and run the uploader without publishing a host port:

```bash
docker network create --internal uploader-backend
docker run --name file-uploader -it --rm \
  --network uploader-backend --network-alias file-uploader \
  -v file-uploader-data:/tmp/uploaded \
  -e MAX_FILE_SIZE_BYTES=104857600 \
  -e MAX_FILES_PER_REQUEST=10 \
  file-uploader
```

Other containers on `uploader-backend` can reach the service at
`http://file-uploader`. No host port is exposed.

`File Uploader` code is under `/app`; container logs are sent to stdout/stderr.

## Environment variables

Here is the list of environment variables that are used:

- `UPLOAD_FOLDER`: Path to the folder to store the uploaded files.
- `SUPPORTED_EXTENSIONS`: Optional comma-separated allowlist, such as `.pdf,.png`. Use lowercase extensions with the leading dot.
- `MAX_FILE_SIZE_BYTES`: Maximum size of an individual uploaded file in bytes (default: `104857600`, or 100 MiB).
- `MAX_FILES_PER_REQUEST`: Maximum number of files accepted in one upload request (default: `10`).
- [WEB_CONCURRENCY](https://www.uvicorn.org/settings/#production):
  The number of worker processes for handling requests.
- [WEB_KEEP_ALIVE](https://www.uvicorn.org/settings/#timeouts):
  The number of seconds to wait for requests on a Keep-Alive connection.
- `WEB_GRACEFUL_SHUTDOWN_TIMEOUT`: Seconds to wait for active requests to finish during shutdown.

Set these variables in the service environment before starting it. The upload
limits must be positive integers and take effect after the service restarts.
The application checks file size after multipart parsing; also configure a
maximum request-body size at the reverse proxy or cluster ingress to reject
oversized requests before they are parsed.
