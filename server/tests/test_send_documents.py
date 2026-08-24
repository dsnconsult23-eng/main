import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config import Config
from db.database import _detect_document_extension, save_policy_documents


class FakeCursor:
    def __init__(self):
        self.executions = []

    def execute(self, sql, params):
        self.executions.append((sql, params))


class FakeConnection:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1


class SendDocumentsStorageTests(unittest.TestCase):
    def test_extension_is_detected_from_file_content(self):
        self.assertEqual(".pdf", _detect_document_extension(b"%PDF-1.4\n"))
        self.assertEqual(".jpg", _detect_document_extension(b"\xff\xd8\xff\xe0JFIF"))

    def test_repeated_requests_do_not_overwrite_existing_documents(self):
        encoded = base64.b64encode(b"%PDF-1.4\n%%EOF\n").decode("ascii")
        cursor = FakeCursor()
        connection = FakeConnection()

        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            Config, "DOCUMENT_STORAGE_PATH", temp_dir
        ):
            save_policy_documents("40/020336", [encoded], cursor, connection)
            save_policy_documents("40/020336", [encoded], cursor, connection)
            saved_files = list(Path(temp_dir).rglob("*.pdf"))

        self.assertEqual(2, len(saved_files))
        self.assertNotEqual(saved_files[0].name, saved_files[1].name)
        self.assertEqual(2, len(cursor.executions))
        self.assertEqual(2, connection.commits)


if __name__ == "__main__":
    unittest.main()
