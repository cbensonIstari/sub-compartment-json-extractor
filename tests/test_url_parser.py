import pytest
from src.url_parser import parse_istari_url, validate_uuid


class TestParseIstariUrl:
    def test_standard_url(self):
        url = "https://demo.istari.app/files/f7c6d97d-630b-4193-884b-e689e6626612/5ea06ed9-132e-42ef-9b6e-cef8628e4939"
        result = parse_istari_url(url)
        assert result["host"] == "demo.istari.app"
        assert result["workspace_id"] == "f7c6d97d-630b-4193-884b-e689e6626612"
        assert result["file_id"] == "5ea06ed9-132e-42ef-9b6e-cef8628e4939"

    def test_url_without_scheme(self):
        url = "demo.istari.app/files/abc-123/def-456"
        result = parse_istari_url(url)
        assert result["host"] == "demo.istari.app"
        assert result["workspace_id"] == "abc-123"
        assert result["file_id"] == "def-456"

    def test_url_with_trailing_slash(self):
        url = "https://demo.istari.app/files/ws-id/file-id/"
        result = parse_istari_url(url)
        assert result["file_id"] == "file-id"

    def test_invalid_url_no_files_segment(self):
        with pytest.raises(ValueError, match="Invalid Istari URL"):
            parse_istari_url("https://demo.istari.app/other/ws/file")

    def test_invalid_url_too_short(self):
        with pytest.raises(ValueError, match="Invalid Istari URL"):
            parse_istari_url("https://demo.istari.app/files/only-one")

    def test_custom_host(self):
        url = "https://mycompany.istari.app/files/ws-1/file-1"
        result = parse_istari_url(url)
        assert result["host"] == "mycompany.istari.app"


class TestValidateUuid:
    def test_valid_uuid(self):
        assert validate_uuid("f7c6d97d-630b-4193-884b-e689e6626612") is True

    def test_invalid_uuid(self):
        assert validate_uuid("not-a-uuid") is False

    def test_uppercase_uuid(self):
        assert validate_uuid("F7C6D97D-630B-4193-884B-E689E6626612") is True

    def test_empty_string(self):
        assert validate_uuid("") is False
