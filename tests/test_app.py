import io
import os
import tempfile
from unittest import TestCase

from fastapi.testclient import TestClient


class AppTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        from uploader.app import app

        cls.upload_directory = tempfile.TemporaryDirectory()
        app.state.upload_folder = cls.upload_directory.name
        cls.client = TestClient(app, base_url="http://localhost")
        cls.content = b"pass"

    @classmethod
    def tearDownClass(cls):
        cls.upload_directory.cleanup()

    def test_main_page(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["swagger"], "http://localhost/openapi/swagger")

    def test_upload(self):
        response = self.client.post(
            "/files/", files={"file[]": ("test.py", self.content)}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [{"name": "test.py", "url": "http://localhost/files/test.py"}],
        )

        response = self.client.get("/files/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [{"name": "test.py", "url": "http://localhost/files/test.py"}],
        )

        response = self.client.get("/files/test.py")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, self.content)

        response = self.client.get("/files/", params={"filter": "*.py"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

        response = self.client.delete("/files/test.py")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True})

    def test_upload_folder(self):
        response = self.client.post(
            "/files/",
            files={"file[]": ("test.py", self.content)},
            data={"folder": "test"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [
                {
                    "name": "test.py",
                    "url": "http://localhost/files/test/test.py",
                }
            ],
        )

        response = self.client.get("/files/")

        self.assertEqual(
            response.json(),
            [
                {
                    "name": "test.py",
                    "url": "http://localhost/files/test/test.py",
                }
            ],
        )

        response = self.client.get("/files/test/test.py")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, self.content)

        response = self.client.delete("/files/test/test.py")

        self.assertEqual(response.status_code, 200)

    def test_empty(self):
        response = self.client.post(
            "/files/", files={"file[]": ("", io.BytesIO())}
        )

        self.assertEqual(response.status_code, 400)

    def test_no_files(self):
        response = self.client.post("/files/", data={})

        self.assertEqual(response.status_code, 422)

    def test_path_injection(self):
        response = self.client.post(
            "/files/",
            files={"file[]": ("test.py", self.content)},
            data={"folder": "../../test"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {
                "code": 400,
                "description": "../../test folder is not allowed!",
                "name": "Bad Request",
            },
        )

    def test_file_filter_does_not_accept_path_segments(self):
        response = self.client.get("/files/", params={"filter": "../*.py"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_upload_rejects_file_above_size_limit(self):
        from uploader import app as uploader

        original_limit = uploader.MAX_FILE_SIZE_BYTES
        uploader.MAX_FILE_SIZE_BYTES = 3
        try:
            response = self.client.post(
                "/files/", files={"file[]": ("large.txt", b"four")}
            )
        finally:
            uploader.MAX_FILE_SIZE_BYTES = original_limit

        self.assertEqual(response.status_code, 413)
        self.assertEqual(self.client.get("/files/").json(), [])

    def test_upload_rejects_too_many_files(self):
        from uploader import app as uploader

        original_limit = uploader.MAX_FILES_PER_REQUEST
        uploader.MAX_FILES_PER_REQUEST = 1
        try:
            response = self.client.post(
                "/files/",
                files=[
                    ("file[]", ("first.txt", b"first")),
                    ("file[]", ("second.txt", b"second")),
                ],
            )
        finally:
            uploader.MAX_FILES_PER_REQUEST = original_limit

        self.assertEqual(response.status_code, 413)
        self.assertEqual(self.client.get("/files/").json(), [])

    def test_symlink_to_outside_is_not_accessible(self):
        from uploader.app import app

        with tempfile.TemporaryDirectory() as outside_directory:
            outside_file = os.path.join(outside_directory, "outside.txt")
            with open(outside_file, "wb") as output:
                output.write(self.content)

            link_path = os.path.join(app.state.upload_folder, "escape.txt")
            try:
                os.symlink(outside_file, link_path)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Symlinks are not available: {error}")

            self.assertEqual(self.client.get("/files/escape.txt").status_code, 404)
            self.assertEqual(self.client.delete("/files/escape.txt").status_code, 404)
            self.assertEqual(self.client.get("/files/?filter=escape.txt").json(), [])

    def test_supported_extensions_are_enforced(self):
        from uploader import app as uploader

        original_extensions = uploader.supported_extensions
        uploader.supported_extensions = [".txt"]
        try:
            response = self.client.post(
                "/files/", files={"file[]": ("blocked.py", self.content)}
            )
        finally:
            uploader.supported_extensions = original_extensions

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["description"], "blocked.py is not allowed")

    def test_upload_sanitizes_path_components_from_filename(self):
        response = self.client.post(
            "/files/", files={"file[]": ("../../file name.txt", self.content)}
        )

        self.assertEqual(response.status_code, 200)
        uploaded_file = response.json()[0]
        self.assertNotIn("/", uploaded_file["name"])
        self.assertNotIn("\\", uploaded_file["name"])
        self.assertTrue(uploaded_file["name"].endswith(".txt"))
        self.assertEqual(self.client.get(uploaded_file["url"]).content, self.content)
        self.assertEqual(self.client.delete(uploaded_file["url"]).status_code, 200)

    def test_wrong_data(self):
        response = self.client.post(
            "/files/",
            json={"data": [{"col1": 1, "col2": 1}, {"col1": 2, "col2": 2}]},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()[0]["type"], "missing")

    def test_delete_non_existing_file(self):
        response = self.client.delete("/files/__not_exist__.py")

        self.assertEqual(response.status_code, 404)

    def test_non_existent_endpoint(self):
        response = self.client.get("/non_existent_endpoint")

        self.assertEqual(response.status_code, 404)
