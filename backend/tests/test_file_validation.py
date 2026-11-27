import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile
from io import BytesIO
from app.config import settings
from app.db import connect, init_db
from app.files import safe_path, validate_file_content

class FileValidationTests(unittest.TestCase):
    def test_rejects_empty_and_mismatched_pdf(self):
        with self.assertRaises(ValueError):
            validate_file_content("a.txt", b"")
        with self.assertRaises(ValueError):
            validate_file_content("a.pdf", b"not a pdf")

    def test_rejects_binary_text_and_fake_excel(self):
        with self.assertRaises(ValueError):
            validate_file_content("a.txt", b"hello\\x00world")
        with self.assertRaises(ValueError):
            validate_file_content("a.xlsx", b"PK\\x03\\x04not a zip")

    def test_accepts_minimal_valid_excel_zip_container(self):
        buf=BytesIO()
        with ZipFile(buf,"w") as z:
            z.writestr("[Content_Types].xml","<Types/>")
            z.writestr("xl/workbook.xml","<workbook/>")
        validate_file_content("a.xlsx",buf.getvalue())

    def test_rejects_unsupported_extension(self):
        with self.assertRaises(ValueError):
            safe_path("payload.exe")

if __name__ == "__main__":
    unittest.main()
