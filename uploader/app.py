import glob
import os
from typing import List

from flask import abort, jsonify, send_from_directory, url_for
from flask_cors import CORS
from flask_openapi3 import FileStorage, Info, OpenAPI, Tag
from pydantic import BaseModel, Field
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename

from . import __version__

__name__ = "File Uploader"
__upload_folder__ = os.environ.get("UPLOAD_FOLDER", "/tmp/uploaded")
SUPPORTED_EXTENSIONS = os.environ.get("SUPPORTED_EXTENSIONS")
supported_extensions = None
if SUPPORTED_EXTENSIONS:
    supported_extensions = [
        x.strip() for x in os.environ.get("SUPPORTED_EXTENSIONS").split(",")
    ]


def is_file_allowed(file_name: str):
    if supported_extensions:
        _, extension = os.path.splitext(file_name.lower())
        return extension in supported_extensions
    return True


def is_access_allowed(folder):
    return (
        os.path.commonprefix((os.path.realpath(folder), app.config["UPLOAD_FOLDER"]))
        == app.config["UPLOAD_FOLDER"]
    )


class Information(BaseModel):
    name: str = Field(__name__, description="Name of the file uploader")
    version: str = Field(__version__, description="Version of the file uploader")
    uploadFolder: str = Field(
        __upload_folder__, description="Files are stored in this folder"
    )
    swagger: str = Field("/openapi/swagger", description="Swagger URL")


class FileForm(BaseModel):
    file: List[FileStorage] = Field(..., alias="file[]")
    folder: str = Field(None, description="Folder to store")


class FilePath(BaseModel):
    file_name: str = Field(..., description="File Name")


class File(BaseModel):
    name: str = Field(..., description="File Name")
    url: str = Field(..., description="Download URL")


class Files(BaseModel):
    files: list[File] = Field(..., description="Files")


class FileQuery(BaseModel):
    filter: str = Field("*", description="File filter in glob pattern format")
    start: int = Field(
        -1, description="Starting file, leave empty or put -1 to return all files"
    )
    limit: int = Field(20, description="Number of files to return")


app = OpenAPI(
    __name__,
    info=Info(title=__name__, version=__version__),
)
app_tag = Tag(name=__name__, description="A Simple File Uploader")


# Set application configuration
app.config.update(
    {
        # The SECRET_KEY is needed to keep the client-side sessions secure.
        # <https://flask.palletsprojects.com/en/2.0.x/quickstart/#sessions>
        # <https://stackoverflow.com/a/34903502>
        # <https://stackoverflow.com/a/22463969>
        # <https://stackoverflow.com/a/27287455>
        "SECRET_KEY": os.urandom(20).hex(),
        # If upload folder is not defined, use the default path
        "UPLOAD_FOLDER": __upload_folder__,
        # Read image version from file
        "VERSION": __version__,
        "NAME": __name__,
    }
)

# CSRF protection is not needed with bearer token.
# <https://security.stackexchange.com/a/170414>
# <https://security.stackexchange.com/a/166798>
# Enable safe CORS policy
CORS(app, resources={r"/*": {"origins": "*", "send_wildcard": "False"}})


@app.get("/", tags=[app_tag], responses={"200": Information})
def index():
    return jsonify(
        {
            "name": app.config["NAME"],
            "version": app.config["VERSION"],
            "uploadFolder": app.config["UPLOAD_FOLDER"],
            "swagger": url_for("openapi.swagger", _external=True),
        }
    )


@app.get("/files/", tags=[app_tag], responses={"200": Files})
def files(query: FileQuery):
    app.logger.info(
        f"Filtering files with {query.filter} at {app.config['UPLOAD_FOLDER']}"
    )
    # get all files
    files = glob.glob(f"{app.config['UPLOAD_FOLDER']}/{query.filter}")
    # sort files by date
    files.sort(key=os.path.getmtime)
    names = [os.path.basename(x) for x in files]
    if query.start > -1:
        # just return the current page
        app.logger.info(
            f"Starting with {query.start}. file and returning {query.limit} files"
        )
        names = names[query.start : query.limit]
    return jsonify(
        [
            {
                "name": name,
                "url": url_for("files", file_name=name, _external=True),
            }
            for name in names
        ]
    )


@app.get("/files/<path:file_name>", tags=[app_tag])
def get_file(path: FilePath):
    if path.file_name:
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], path.file_name)
        if is_access_allowed(file_path):
            return send_from_directory(app.config["UPLOAD_FOLDER"], path.file_name)


@app.delete("/files/<path:file_name>", tags=[app_tag])
def delete(path: FilePath):
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], path.file_name)
    if os.path.exists(file_path):
        os.remove(file_path)
        app.logger.info(f"Successfully deleted {path.file_name} file")
        return jsonify(success=True)
    else:
        abort(404, "File doesn't exist")


def create_upload_folder(folder):
    if not os.path.exists(app.config["UPLOAD_FOLDER"]):
        # create the upload folder if it doesn't exist
        os.makedirs(app.config["UPLOAD_FOLDER"])
        app.logger.info(f"Created {app.config['UPLOAD_FOLDER']} folder")
    upload_folder = app.config["UPLOAD_FOLDER"]
    if folder:
        upload_folder = os.path.join(app.config["UPLOAD_FOLDER"], folder)
        if not is_access_allowed(upload_folder):
            abort(400, f"{folder} folder is not allowed!")
        if not os.path.exists(upload_folder):
            # create the upload folder if it doesn't exist
            os.makedirs(upload_folder)
            app.logger.info(f"Created {upload_folder} folder")
    return upload_folder


def upload_file(folder, upload_folder, file):
    if file.filename == "":
        abort(400, "File is not selected")
    if is_file_allowed(file.filename) is False:
        abort(400, f"{file.filename} is not allowed")
    file_name = secure_filename(file.filename)
    file_path = os.path.join(upload_folder, file_name)
    # save the uploaded file to the upload folder
    file.save(file_path)
    # generate the url of the uploaded file
    file_url = url_for(
        "get_file",
        file_name=os.path.join(folder if folder else "", file_name),
        _external=True,
    )
    return file_name, file_url


@app.post("/files/", tags=[app_tag])
def upload(form: FileForm):
    files = form.file
    folder = form.folder
    uploaded_files = []
    if len(files) > 0:
        upload_folder = create_upload_folder(folder)
        for file in files:
            file_name, file_url = upload_file(folder, upload_folder, file)
            app.logger.info(f"Successfully uploaded {file_url} file")
            uploaded_files.append({"name": file_name, "url": file_url})
        return jsonify(uploaded_files)
    else:
        abort(400, "No file is selected!")


@app.errorhandler(Exception)
def handle_exception(e):
    """Return JSON instead of HTML for exceptions and errors"""
    if isinstance(e, HTTPException):
        # handle HTTP exception
        return (
            jsonify(
                {
                    "code": e.code,
                    "name": e.name,
                    "description": e.description,
                }
            ),
            e.code,
        )

    # handle non-HTTP exceptions
    return (
        jsonify(
            {
                "code": 500,
                "name": "Internal Server Error",
                "description": f"{e}",
            }
        ),
        500,
    )
