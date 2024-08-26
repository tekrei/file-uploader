import io
from unittest import TestCase


class AppTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        from uploader import app

        app = app.app
        app.config["TESTING"] = True
        cls.client = app.test_client()
        cls.content = b"pass"

    def test_main_page(self):
        response = self.client.get("/", follow_redirects=True)

        self.assertEqual(response.status_code, 200)

    def test_upload(self):
        response = self.client.post(
            "/files/", data={"file[]": (io.BytesIO(self.content), "test.py")}
        )

        self.assertEqual(response.status_code, 200)

        response = self.client.get("/files/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            response.json,
            [{"name": "test.py", "url": "http://localhost/files/test.py"}],
        )

        response = self.client.get("/files/test.py")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, self.content)

        response = self.client.delete("/files/test.py")

        self.assertEqual(response.status_code, 200)

    def test_upload_folder(self):
        response = self.client.post(
            "/files/",
            data={"file[]": (io.BytesIO(self.content), "test.py"), "folder": "test"},
        )

        self.assertEqual(response.status_code, 200)

        response = self.client.get("/files/")

        self.assertTrue(
            response.json,
            [{"name": "test.py", "url": "http://localhost/files/test/test.py"}],
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/files/test/test.py")

        self.assertEqual(response.data, self.content)
        self.assertEqual(response.status_code, 200)

        response = self.client.delete("/files/test/test.py")

        self.assertEqual(response.status_code, 200)

    def test_empty(self):
        response = self.client.post("/files/", data={"file[]": (io.BytesIO(), "")})

        self.assertEqual(response.status_code, 400)

    def test_no_files(self):
        response = self.client.post("/files/", data={"file[]": []})

        self.assertEqual(response.status_code, 400)

    def test_path_injection(self):
        response = self.client.post(
            "/files/",
            data={
                "file[]": (io.BytesIO(self.content), "test.py"),
                "folder": "../../test",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json,
            {
                "code": 400,
                "description": "../../test folder is not allowed!",
                "name": "Bad Request",
            },
        )

    def test_wrong_data(self):
        response = self.client.post(
            "/files/",
            json={"data": [{"col1": 1, "col2": 1}, {"col1": 2, "col2": 2}]},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual("No file is selected!", response.json["description"])

    def test_delete_non_existing_file(self):
        response = self.client.delete("/files/__not_exist__.py")

        self.assertEqual(response.status_code, 404)

    def test_non_existent_endpoint(self):
        response = self.client.get("/non_existent_endpoint")

        self.assertEqual(response.status_code, 404)
