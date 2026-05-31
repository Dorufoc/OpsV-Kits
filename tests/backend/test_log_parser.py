import pytest

from app.services.log_parser_service import LogParserService


@pytest.fixture
def parser():
    return LogParserService()


def test_parse_json(parser):
    result = parser.parse('{"level": "ERROR", "message": "something failed", "timestamp": "2024-01-01T00:00:00Z"}')
    assert result["format"] == "json"
    assert result["level"] == "ERROR"
    assert result["message"] == "something failed"


def test_parse_key_value(parser):
    result = parser.parse('level=ERROR msg="connection timeout" service=api')
    assert result["format"] == "key_value"
    assert result["level"] == "ERROR"


def test_parse_syslog(parser):
    result = parser.parse("<134>Jan  1 00:00:00 myhost myapp[1234]: something happened")
    assert result["format"] == "syslog"
    assert result["fields"]["hostname"] == "myhost"


def test_parse_unstructured(parser):
    result = parser.parse("just some random text without structure")
    assert result["format"] == "unstructured"
    assert result["message"] == "just some random text without structure"


def test_extract_level_error(parser):
    level = parser.extract_level("ERROR: something went wrong")
    assert level == "ERROR"


def test_extract_level_warn(parser):
    level = parser.extract_level("WARNING: disk space low")
    assert level == "WARN"


def test_extract_level_info(parser):
    level = parser.extract_level("INFO: application started")
    assert level == "INFO"


def test_extract_level_debug(parser):
    level = parser.extract_level("DEBUG: variable value")
    assert level == "DEBUG"


def test_extract_level_critical(parser):
    level = parser.extract_level("CRITICAL: system failure")
    assert level == "CRITICAL"


def test_extract_level_fatal(parser):
    level = parser.extract_level("FATAL: unrecoverable error")
    assert level == "CRITICAL"


def test_parse_json_with_nested_fields(parser):
    result = parser.parse('{"level": "INFO", "msg": "request", "request": {"path": "/api", "method": "GET"}}')
    assert result["format"] == "json"
    assert result["fields"]["request"]["path"] == "/api"


def test_parse_empty_string(parser):
    result = parser.parse("")
    assert result["format"] == "unstructured"


def test_parse_csv(parser):
    result = parser.parse("timestamp,level,source,message\n2024-01-01,ERROR,api,connection failed")
    assert result["format"] == "csv"
    assert result["level"] == "ERROR"


def test_parse_timestamp_iso(parser):
    ts = parser.parse_timestamp("2024-01-01T12:00:00Z")
    assert ts is not None
    assert ts > 0


def test_parse_timestamp_unix(parser):
    ts = parser.parse_timestamp("1704110400")
    assert ts is not None
    assert abs(ts - 1704110400) < 1
