import fnmatch
import logging
import os
import shutil
from http import HTTPStatus
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pathvalidate import sanitize_filename
from pydantic import BaseModel, Field

from . import __version__

APP_NAME = "File Uploader"
UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "/tmp/uploaded")
SUPPORTED_EXTENSIONS = os.environ.get("SUPPORTED_EXTENSIONS")
MAX_FILE_SIZE_BYTES = int(os.environ.get("MAX_FILE_SIZE_BYTES", "104857600"))
MAX_FILES_PER_REQUEST = int(os.environ.get("MAX_FILES_PER_REQUEST", "10"))
if MAX_FILE_SIZE_BYTES < 1 or MAX_FILES_PER_REQUEST < 1:
    raise ValueError("Upload limits must be positive integers")
supported_extensions = None
if SUPPORTED_EXTENSIONS:
    supported_extensions = [
        extension.strip() for extension in SUPPORTED_EXTENSIONS.split(",")
    ]

logger = logging.getLogger(__name__)


class Information(BaseModel):
    name: str = Field(APP_NAME, description="Name of the file uploader")
    version: str = Field(__version__, description="Version of the file uploader")
    uploadFolder: str = Field(
        UPLOAD_FOLDER, description="Files are stored in this folder"
    )
    swagger: str = Field("/openapi/swagger", description="Swagger URL")


class FileInfo(BaseModel):
    name: str = Field(..., description="File Name")
    url: str = Field(..., description="Download URL")


app = FastAPI(
    title=APP_NAME,
    version=__version__,
    docs_url="/openapi/swagger",
    openapi_url="/openapi/openapi.json",
)
app.state.upload_folder = UPLOAD_FOLDER
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _is_file_allowed(file_name: str) -> bool:
    if supported_extensions:
        _, extension = os.path.splitext(file_name.lower())
        return extension in supported_extensions
    return True


def _get_upload_root() -> str:
    return os.path.realpath(app.state.upload_folder)


def _is_access_allowed(folder: str) -> bool:
    root = _get_upload_root()
    try:
        return os.path.commonpath((os.path.realpath(folder), root)) == root
    except ValueError:
        return False


def _resolve_upload_path(
    relative_path: str,
    *,
    status_code: int = 404,
    detail: str = "File doesn't exist",
) -> str:
    parts = relative_path.replace("\\", "/").split("/")
    safe_parts = [os.path.basename(part) for part in parts]
    if (
        not relative_path
        or any(part in ("", ".", "..") for part in parts)
        or any(safe != part for safe, part in zip(safe_parts, parts))
        or any(sanitize_filename(part, platform="universal") != part for part in parts)
        or any(not part for part in safe_parts)
    ):
        raise HTTPException(status_code=status_code, detail=detail)

    file_path = os.path.join(_get_upload_root(), *safe_parts)
    if not _is_access_allowed(file_path):
        raise HTTPException(status_code=status_code, detail=detail)
    return file_path


@app.get("/", response_model=Information)
def index(request: Request):
    return {
        "name": APP_NAME,
        "version": __version__,
        "uploadFolder": app.state.upload_folder,
        "swagger": str(request.url_for("swagger_ui_html")),
    }


@app.get("/files/", response_model=list[FileInfo])
def files(
    request: Request,
    filter: str = "*",
    start: int = -1,
    limit: int = 20,
):
    logger.info("Filtering files with %s at %s", filter, app.state.upload_folder)
    upload_root = _get_upload_root()
    paths = []
    for directory, subdirectories, file_names in os.walk(upload_root):
        subdirectories[:] = [
            name
            for name in subdirectories
            if _is_access_allowed(os.path.join(directory, name))
        ]
        for file_name in file_names:
            path = os.path.join(directory, file_name)
            relative_path = os.path.relpath(path, upload_root).replace(os.sep, "/")
            if (
                os.path.isfile(path)
                and _is_access_allowed(path)
                and (
                    fnmatch.fnmatchcase(file_name, filter)
                    or fnmatch.fnmatchcase(relative_path, filter)
                )
            ):
                paths.append(path)
    paths.sort(key=os.path.getmtime)
    if start > -1:
        logger.info("Starting with %s. file and returning %s files", start, limit)
        paths = paths[start : start + limit]
    return [
        {
            "name": os.path.basename(path),
            "url": str(
                request.url_for(
                    "get_file",
                    file_name=os.path.relpath(path, upload_root).replace(os.sep, "/"),
                )
            ),
        }
        for path in paths
    ]


@app.get("/files/{file_name:path}", name="get_file")
def get_file(file_name: str):
    file_path = _resolve_upload_path(file_name)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File doesn't exist")
    return FileResponse(file_path)


@app.delete("/files/{file_name:path}")
def delete(file_name: str):
    file_path = _resolve_upload_path(file_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File doesn't exist")
    os.remove(file_path)
    logger.info("Successfully deleted %s file", file_name)
    return {"success": True}


def _create_upload_folder(folder: str | None) -> str:
    upload_root = _get_upload_root()
    os.makedirs(upload_root, exist_ok=True)
    upload_folder = upload_root
    if folder:
        upload_folder = _resolve_upload_path(
            folder,
            status_code=400,
            detail=f"{folder} folder is not allowed!",
        )
        os.makedirs(upload_folder, exist_ok=True)
    return upload_folder


def _upload_file(
    request: Request,
    upload_folder: str,
    file: UploadFile,
) -> FileInfo:
    if not file.filename:
        raise HTTPException(status_code=400, detail="File is not selected")
    if not _is_file_allowed(file.filename):
        raise HTTPException(status_code=400, detail=f"{file.filename} is not allowed")
    file_name = os.path.basename(
        sanitize_filename(file.filename, platform="universal").replace("\\", "/")
    )
    if not file_name:
        raise HTTPException(status_code=400, detail="File name is not valid")
    relative_folder = os.path.relpath(
        upload_folder, _get_upload_root()
    )
    relative_path = (
        file_name
        if relative_folder == "."
        else os.path.join(relative_folder, file_name)
    )
    file_path = _resolve_upload_path(relative_path)
    with open(file_path, "wb") as destination:
        shutil.copyfileobj(file.file, destination)
    file_url_path = os.path.relpath(
        file_path, _get_upload_root()
    ).replace(os.sep, "/")
    file_url = str(request.url_for("get_file", file_name=file_url_path))
    return FileInfo(name=file_name, url=file_url)


@app.post("/files/", response_model=list[FileInfo])
def upload(
    request: Request,
    files: Annotated[list[UploadFile], File(alias="file[]")],
    folder: Annotated[str | None, Form()] = None,
):
    if not files:
        raise HTTPException(status_code=400, detail="No file is selected!")
    if len(files) > MAX_FILES_PER_REQUEST:
        raise HTTPException(
            status_code=413,
            detail=f"No more than {MAX_FILES_PER_REQUEST} files may be uploaded per request",
        )
    if any(file.size is None or file.size > MAX_FILE_SIZE_BYTES for file in files):
        raise HTTPException(
            status_code=413,
            detail=f"Each file must be no larger than {MAX_FILE_SIZE_BYTES} bytes",
        )
    upload_folder = _create_upload_folder(folder)
    uploaded_files = []
    for file in files:
        uploaded_file = _upload_file(request, upload_folder, file)
        logger.info("Successfully uploaded %s file", uploaded_file.url)
        uploaded_files.append(uploaded_file)
    return uploaded_files


@app.exception_handler(HTTPException)
async def handle_http_exception(request: Request, exception: HTTPException):
    del request
    return JSONResponse(
        status_code=exception.status_code,
        content={
            "code": exception.status_code,
            "name": HTTPStatus(exception.status_code).phrase,
            "description": str(exception.detail),
        },
        headers=exception.headers,
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_exception(
    request: Request, exception: RequestValidationError
):
    del request
    errors = exception.errors()
    if any(
        error.get("loc", ())[:2] == ("body", "file[]")
        and error.get("input") == ""
        for error in errors
    ):
        return JSONResponse(
            status_code=400,
            content={
                "code": 400,
                "name": HTTPStatus(400).phrase,
                "description": "File is not selected",
            },
        )
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder(errors),
    )


@app.exception_handler(Exception)
async def handle_exception(request: Request, exception: Exception):
    del request
    logger.error(
        "Unhandled request exception",
        exc_info=(type(exception), exception, exception.__traceback__),
    )
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "name": "Internal Server Error",
            "description": str(exception),
        },
    )