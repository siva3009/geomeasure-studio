"""
Tests for file validation service.
"""

import os
import pytest
from app.services.file_validator import (
    validate_file_extension,
    validate_file_size,
    get_safe_filename,
    FileValidationError,
)


class TestValidateFileExtension:
    def test_kml_accepted(self):
        assert validate_file_extension("data.kml") == ".kml"

    def test_zip_accepted(self):
        assert validate_file_extension("shapefile.zip") == ".zip"

    def test_uppercase_kml_accepted(self):
        assert validate_file_extension("DATA.KML") == ".kml"

    def test_txt_rejected(self):
        with pytest.raises(FileValidationError) as exc:
            validate_file_extension("file.txt")
        assert exc.value.status_code == 415

    def test_no_extension_rejected(self):
        with pytest.raises(FileValidationError) as exc:
            validate_file_extension("noext")
        assert exc.value.status_code == 415

    def test_empty_filename_rejected(self):
        with pytest.raises(FileValidationError):
            validate_file_extension("")

    def test_path_traversal_stripped(self):
        """Ensure only basename is used — path traversal in name is harmless."""
        result = validate_file_extension("../../etc/data.kml")
        assert result == ".kml"


class TestValidateFileSize:
    def test_valid_size(self):
        content = b"x" * 100
        assert validate_file_size(content) == 100

    def test_empty_rejected(self):
        with pytest.raises(FileValidationError):
            validate_file_size(b"")


class TestGetSafeFilename:
    def test_strips_path(self):
        assert get_safe_filename("/path/to/file.kml") == "file.kml"

    def test_strips_windows_path(self):
        assert get_safe_filename("C:\\Users\\data.zip") == "data.zip"

    def test_preserves_simple_name(self):
        assert get_safe_filename("simple.kml") == "simple.kml"
