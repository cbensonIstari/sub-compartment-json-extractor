import pytest
from src.json_navigator import (
    describe_value,
    display_structure,
    resolve_path,
    preview_json,
    suggest_filename,
)

SAMPLE_DATA = {
    "metadata": {
        "version": "1.0",
        "author": "test",
    },
    "components": [
        {"id": "comp-001", "name": "Engine", "type": "propulsion"},
        {"id": "comp-002", "name": "Wing", "type": "structure"},
        {"id": "comp-003", "name": "Avionics", "type": "electronics"},
    ],
    "parameters": {
        "weight": 5000,
        "max_speed": 300.5,
        "active": True,
    },
    "notes": None,
}


class TestDescribeValue:
    def test_dict(self):
        assert describe_value({"a": 1, "b": 2}) == "object, 2 keys"

    def test_list(self):
        assert describe_value([1, 2, 3]) == "array, 3 items"

    def test_string_short(self):
        assert describe_value("hello") == 'string: "hello"'

    def test_string_long(self):
        long_str = "a" * 50
        desc = describe_value(long_str)
        assert "..." in desc

    def test_number_int(self):
        assert describe_value(42) == "number: 42"

    def test_number_float(self):
        assert describe_value(3.14) == "number: 3.14"

    def test_boolean(self):
        assert describe_value(True) == "boolean: true"

    def test_null(self):
        assert describe_value(None) == "null"


class TestResolvePath:
    def test_top_level_key(self):
        result = resolve_path(SAMPLE_DATA, "metadata")
        assert result == {"version": "1.0", "author": "test"}

    def test_nested_key(self):
        result = resolve_path(SAMPLE_DATA, "metadata.version")
        assert result == "1.0"

    def test_array_index(self):
        result = resolve_path(SAMPLE_DATA, "components[0]")
        assert result["id"] == "comp-001"

    def test_array_index_nested(self):
        result = resolve_path(SAMPLE_DATA, "components[1].name")
        assert result == "Wing"

    def test_jsonpath_root(self):
        result = resolve_path(SAMPLE_DATA, "$.metadata.version")
        assert result == "1.0"

    def test_jsonpath_root_only(self):
        result = resolve_path(SAMPLE_DATA, "$")
        assert result == SAMPLE_DATA

    def test_nonexistent_key(self):
        with pytest.raises(KeyError, match="not found"):
            resolve_path(SAMPLE_DATA, "nonexistent")

    def test_index_out_of_range(self):
        with pytest.raises(IndexError, match="out of range"):
            resolve_path(SAMPLE_DATA, "components[99]")

    def test_navigate_into_scalar(self):
        with pytest.raises(KeyError):
            resolve_path(SAMPLE_DATA, "metadata.version.deep")

    def test_bare_bracket_index(self):
        data = [{"a": 1}, {"a": 2}]
        result = resolve_path(data, "[1]")
        assert result == {"a": 2}


class TestDisplayStructure:
    def test_returns_lines(self):
        lines = display_structure(SAMPLE_DATA, max_depth=1)
        assert len(lines) == 4  # metadata, components, parameters, notes

    def test_line_format(self):
        lines = display_structure(SAMPLE_DATA, max_depth=1)
        display, key = lines[0]
        assert '"metadata"' in display
        assert key == "metadata"

    def test_list_structure(self):
        lines = display_structure([1, 2, 3], max_depth=1)
        assert len(lines) == 3


class TestPreviewJson:
    def test_short_json(self):
        result = preview_json({"a": 1})
        assert '"a": 1' in result

    def test_truncation(self):
        big = {f"key_{i}": i for i in range(100)}
        result = preview_json(big, max_lines=5)
        assert "more lines" in result


class TestSuggestFilename:
    def test_basic(self):
        assert suggest_filename("model.json", "components") == "model_components.json"

    def test_no_extension(self):
        assert suggest_filename("model", "metadata") == "model_metadata.json"

    def test_special_chars_in_key(self):
        result = suggest_filename("model.json", "my key/value")
        assert "/" not in result
