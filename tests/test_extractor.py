import json
import os
import pytest
from src.extractor import extract_element, write_temp_json, cleanup_temp_file

SAMPLE_DATA = {
    "metadata": {"version": "2.0"},
    "items": [
        {"id": 1, "name": "Alpha"},
        {"id": 2, "name": "Beta"},
    ],
}


class TestExtractElement:
    def test_extract_top_level(self):
        element, key = extract_element(SAMPLE_DATA, "metadata")
        assert element == {"version": "2.0"}
        assert key == "metadata"

    def test_extract_nested(self):
        element, key = extract_element(SAMPLE_DATA, "metadata.version")
        assert element == "2.0"
        assert key == "version"

    def test_extract_array_item(self):
        element, key = extract_element(SAMPLE_DATA, "items[0]")
        assert element["name"] == "Alpha"

    def test_extract_nonexistent(self):
        with pytest.raises(KeyError):
            extract_element(SAMPLE_DATA, "missing")


class TestWriteTempJson:
    def test_creates_file(self):
        data = {"hello": "world"}
        path = write_temp_json(data, "test.json")
        try:
            assert os.path.exists(path)
            assert path.endswith("test.json")

            with open(path) as f:
                loaded = json.load(f)
            assert loaded == data
        finally:
            cleanup_temp_file(path)

    def test_pretty_printed(self):
        data = {"a": 1, "b": 2}
        path = write_temp_json(data, "formatted.json")
        try:
            with open(path) as f:
                content = f.read()
            assert "\n" in content  # pretty-printed has newlines
            assert "  " in content  # indented
        finally:
            cleanup_temp_file(path)


class TestCleanupTempFile:
    def test_cleanup_removes_file(self):
        path = write_temp_json({"x": 1}, "cleanup_test.json")
        assert os.path.exists(path)
        cleanup_temp_file(path)
        assert not os.path.exists(path)

    def test_cleanup_nonexistent_no_error(self):
        cleanup_temp_file("/tmp/nonexistent_file_12345.json")
