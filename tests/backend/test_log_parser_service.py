from __future__ import annotations

from unittest.mock import patch

import csv

import pytest

from app.services.log_parser_service import LogParserService


@pytest.fixture
def parser():
    return LogParserService()


class TestParseTimestamp:
    def test_iso_with_timezone_offset(self, parser):
        ts = parser.parse_timestamp("2024-01-01T12:00:00+08:00")
        assert ts is not None
        assert ts > 0

    def test_iso_with_plus_and_t(self, parser):
        ts = parser.parse_timestamp("2024-06-15T10:30:00+05:30")
        assert ts is not None

    def test_empty_string(self, parser):
        assert parser.parse_timestamp("") is None

    def test_whitespace_only(self, parser):
        assert parser.parse_timestamp("   ") is None

    def test_zero_float(self, parser):
        assert parser.parse_timestamp("0") is None

    def test_negative_float(self, parser):
        assert parser.parse_timestamp("-1.5") is None

    def test_unix_timestamp(self, parser):
        ts = parser.parse_timestamp("1704110400")
        assert ts is not None
        assert abs(ts - 1704110400) < 1

    def test_syslog_bsd_format(self, parser):
        ts = parser.parse_timestamp("Jan 15 10:30:00")
        assert ts is not None

    def test_syslog_bsd_double_space(self, parser):
        ts = parser.parse_timestamp("Jan  5 10:30:00")
        assert ts is not None

    def test_clf_format(self, parser):
        ts = parser.parse_timestamp("15/Jan/2024:10:30:00")
        assert ts is not None

    def test_unparseable(self, parser):
        assert parser.parse_timestamp("not-a-timestamp") is None

    def test_z_suffix(self, parser):
        ts = parser.parse_timestamp("2024-01-01T12:00:00Z")
        assert ts is not None


class TestParseJson:
    def test_non_dict_returns_none(self, parser):
        result = parser.parse_json("[1, 2, 3]")
        assert result is None

    def test_level_with_partial_match(self, parser):
        result = parser.parse_json('{"level": "ERROR_LEVEL_HIGH", "message": "test"}')
        assert result is not None
        assert result["level"] == "ERROR"

    def test_level_with_severity_key(self, parser):
        result = parser.parse_json('{"severity": "WARN", "message": "test"}')
        assert result is not None
        assert result["level"] == "WARN"

    def test_level_with_lvl_key(self, parser):
        result = parser.parse_json('{"lvl": "DEBUG", "message": "test"}')
        assert result is not None
        assert result["level"] == "DEBUG"

    def test_level_with_log_level_key(self, parser):
        result = parser.parse_json('{"log_level": "INFO", "message": "test"}')
        assert result is not None
        assert result["level"] == "INFO"

    def test_timestamp_with_at_key(self, parser):
        result = parser.parse_json('{"@timestamp": "2024-01-01T12:00:00Z", "message": "test"}')
        assert result is not None
        assert result["timestamp"] is not None

    def test_timestamp_with_ts_key(self, parser):
        result = parser.parse_json('{"ts": "2024-01-01T12:00:00", "message": "test"}')
        assert result is not None
        assert result["timestamp"] is not None

    def test_timestamp_with_datetime_key(self, parser):
        result = parser.parse_json('{"datetime": "2024-01-01 12:00:00", "message": "test"}')
        assert result is not None
        assert result["timestamp"] is not None

    def test_message_with_msg_key(self, parser):
        result = parser.parse_json('{"msg": "hello", "level": "INFO"}')
        assert result is not None
        assert result["message"] == "hello"

    def test_message_with_text_key(self, parser):
        result = parser.parse_json('{"text": "hello", "level": "INFO"}')
        assert result is not None
        assert result["message"] == "hello"

    def test_message_with_log_key(self, parser):
        result = parser.parse_json('{"log": "hello", "level": "INFO"}')
        assert result is not None
        assert result["message"] == "hello"

    def test_extra_fields_preserved(self, parser):
        result = parser.parse_json('{"level": "INFO", "message": "test", "trace_id": "abc123", "duration": 42}')
        assert result is not None
        assert "trace_id" in result["fields"]
        assert "duration" in result["fields"]

    def test_invalid_json(self, parser):
        result = parser.parse_json("not json at all")
        assert result is None

    def test_no_level_key(self, parser):
        result = parser.parse_json('{"message": "no level here"}')
        assert result is not None
        assert result["level"] is None

    def test_no_timestamp_key(self, parser):
        result = parser.parse_json('{"level": "INFO", "message": "no timestamp"}')
        assert result is not None
        assert result["timestamp"] is None

    def test_no_message_key(self, parser):
        result = parser.parse_json('{"level": "INFO"}')
        assert result is not None
        assert result["message"] == ""


class TestParseKeyValue:
    def test_single_pair_returns_none(self, parser):
        result = parser.parse_key_value("level=ERROR")
        assert result is None

    def test_no_pairs_returns_none(self, parser):
        result = parser.parse_key_value("just plain text no pairs")
        assert result is None

    def test_level_with_partial_match(self, parser):
        result = parser.parse_key_value('level=ERROR_TYPE_A msg="test" service=api')
        assert result is not None
        assert result["level"] == "ERROR"

    def test_level_with_severity_key(self, parser):
        result = parser.parse_key_value('severity=WARN msg="test" service=api')
        assert result is not None
        assert result["level"] == "WARN"

    def test_level_with_lvl_key(self, parser):
        result = parser.parse_key_value('lvl=DEBUG msg="test" service=api')
        assert result is not None
        assert result["level"] == "DEBUG"

    def test_timestamp_parsing(self, parser):
        result = parser.parse_key_value('level=INFO timestamp="2024-01-01T12:00:00" msg="test"')
        assert result is not None
        assert result["timestamp"] is not None

    def test_timestamp_with_ts_key(self, parser):
        result = parser.parse_key_value('level=INFO ts="2024-01-01T12:00:00" msg="test"')
        assert result is not None
        assert result["timestamp"] is not None

    def test_quoted_values_stripped(self, parser):
        result = parser.parse_key_value('level=INFO msg="hello world" service=api')
        assert result is not None
        assert result["fields"]["msg"] == "hello world"

    def test_single_quoted_values_stripped(self, parser):
        result = parser.parse_key_value("level=INFO msg='hello world' service=api")
        assert result is not None
        assert result["fields"]["msg"] == "hello world"

    def test_colon_separator(self, parser):
        result = parser.parse_key_value("level: INFO service: api count: 5")
        assert result is not None

    def test_message_from_remaining(self, parser):
        result = parser.parse_key_value("level=INFO some_extra_text_here count=5")
        assert result is not None
        assert result["message"] != ""

    def test_skip_keys_excluded_from_fields(self, parser):
        result = parser.parse_key_value('level=INFO timestamp="2024-01-01T12:00:00" service=api')
        assert result is not None
        assert "level" not in result["fields"]
        assert "timestamp" not in result["fields"]
        assert "service" in result["fields"]


class TestParseSyslog:
    def test_rfc5424_basic(self, parser):
        line = "<35>1 2024-01-01T12:00:00Z myhost myapp 1234 - - connection refused"
        result = parser.parse_syslog(line)
        assert result is not None
        assert result["format"] == "syslog"
        assert result["level"] == "ERROR"
        assert result["fields"]["hostname"] == "myhost"
        assert result["fields"]["app_name"] == "myapp"
        assert result["fields"]["proc_id"] == "1234"
        assert result["message"] == "connection refused"

    def test_rfc5424_with_structured_data(self, parser):
        line = '<165>1 2024-01-01T12:00:00Z myhost myapp 5678 ID47 [exampleSDID@32473 iut="3" eventSource="App"] test message'
        result = parser.parse_syslog(line)
        assert result is not None
        assert "structured_data" in result["fields"]

    def test_rfc5424_nil_hostname(self, parser):
        line = "<34>1 2024-01-01T12:00:00Z - myapp 1234 - - test"
        result = parser.parse_syslog(line)
        assert result is not None
        assert result["fields"]["hostname"] is None

    def test_rfc5424_nil_app_name(self, parser):
        line = "<34>1 2024-01-01T12:00:00Z myhost - 1234 - - test"
        result = parser.parse_syslog(line)
        assert result is not None
        assert result["fields"]["app_name"] is None

    def test_rfc5424_nil_proc_id(self, parser):
        line = "<34>1 2024-01-01T12:00:00Z myhost myapp - - - test"
        result = parser.parse_syslog(line)
        assert result is not None
        assert result["fields"]["proc_id"] is None

    def test_rfc5424_nil_msgid(self, parser):
        line = "<34>1 2024-01-01T12:00:00Z myhost myapp 1234 - - test"
        result = parser.parse_syslog(line)
        assert result is not None
        assert "msgid" not in result["fields"]

    def test_rfc5424_with_msgid(self, parser):
        line = "<34>1 2024-01-01T12:00:00Z myhost myapp 1234 ID47 - test"
        result = parser.parse_syslog(line)
        assert result is not None
        assert result["fields"]["msgid"] == "ID47"

    def test_rfc5424_severity_critical(self, parser):
        line = "<8>1 2024-01-01T12:00:00Z myhost myapp 1234 - - system panic"
        result = parser.parse_syslog(line)
        assert result is not None
        assert result["level"] == "CRITICAL"

    def test_rfc5424_severity_warn(self, parser):
        line = "<36>1 2024-01-01T12:00:00Z myhost myapp 1234 - - disk space low"
        result = parser.parse_syslog(line)
        assert result is not None
        assert result["level"] == "WARN"

    def test_rfc5424_severity_debug(self, parser):
        line = "<39>1 2024-01-01T12:00:00Z myhost myapp 1234 - - trace output"
        result = parser.parse_syslog(line)
        assert result is not None
        assert result["level"] == "DEBUG"

    def test_rfc3164_basic(self, parser):
        line = "<134>Jan  1 00:00:00 myhost myapp[1234]: something happened"
        result = parser.parse_syslog(line)
        assert result is not None
        assert result["format"] == "syslog"
        assert result["fields"]["hostname"] == "myhost"
        assert result["fields"]["app_name"] == "myapp"
        assert result["fields"]["proc_id"] == "1234"

    def test_rfc3164_no_proc_id(self, parser):
        line = "<134>Jan  1 00:00:00 myhost myapp: something happened"
        result = parser.parse_syslog(line)
        assert result is not None
        assert result["fields"]["proc_id"] is None

    def test_no_match(self, parser):
        result = parser.parse_syslog("not a syslog line")
        assert result is None

    def test_rfc5424_structured_data_nil(self, parser):
        line = "<34>1 2024-01-01T12:00:00Z myhost myapp 1234 ID47 - test"
        result = parser.parse_syslog(line)
        assert result is not None
        assert "structured_data" not in result["fields"]


class TestParseCsv:
    def test_csv_error(self, parser):
        with patch("app.services.log_parser_service.csv.reader", side_effect=csv.Error("csv error")):
            result = parser.parse_csv("a,b\n1,2")
            assert result is None

    def test_single_line_returns_none(self, parser):
        result = parser.parse_csv("header_only")
        assert result is None

    def test_column_mismatch_returns_none(self, parser):
        result = parser.parse_csv("a,b,c\n1,2")
        assert result is None

    def test_level_with_partial_match(self, parser):
        result = parser.parse_csv("level,message\nERROR_TYPE,hello")
        assert result is not None
        assert result["level"] == "ERROR"

    def test_level_with_severity_key(self, parser):
        result = parser.parse_csv("severity,message\nWARN,hello")
        assert result is not None
        assert result["level"] == "WARN"

    def test_level_with_lvl_key(self, parser):
        result = parser.parse_csv("lvl,message\nDEBUG,hello")
        assert result is not None
        assert result["level"] == "DEBUG"

    def test_timestamp_parsing(self, parser):
        result = parser.parse_csv("timestamp,level,message\n2024-01-01T12:00:00,INFO,hello")
        assert result is not None
        assert result["timestamp"] is not None

    def test_timestamp_with_ts_key(self, parser):
        result = parser.parse_csv("ts,level,message\n2024-01-01T12:00:00,INFO,hello")
        assert result is not None
        assert result["timestamp"] is not None

    def test_message_fallback_join(self, parser):
        result = parser.parse_csv("col1,col2,col3\nval1,val2,val3")
        assert result is not None
        assert result["message"] == "val1 | val2 | val3"

    def test_message_from_msg_key(self, parser):
        result = parser.parse_csv("msg,level\nhello,INFO")
        assert result is not None
        assert result["message"] == "hello"

    def test_message_from_text_key(self, parser):
        result = parser.parse_csv("text,level\nhello,INFO")
        assert result is not None
        assert result["message"] == "hello"

    def test_message_from_log_key(self, parser):
        result = parser.parse_csv("log,level\nhello,INFO")
        assert result is not None
        assert result["message"] == "hello"

    def test_skip_keys_excluded(self, parser):
        result = parser.parse_csv("level,timestamp,service\nINFO,2024-01-01T12:00:00,api")
        assert result is not None
        assert "level" not in result["fields"]
        assert "timestamp" not in result["fields"]
        assert "service" in result["fields"]

    def test_empty_rows(self, parser):
        with patch("app.services.log_parser_service.csv.reader", return_value=[]):
            result = parser.parse_csv("a,b\n1,2")
            assert result is None


class TestExtractLevel:
    def test_parsed_level_valid(self, parser):
        assert parser.extract_level("test", {"level": "ERROR"}) == "ERROR"

    def test_parsed_level_needs_normalization(self, parser):
        assert parser.extract_level("test", {"level": "WARNING"}) == "WARN"

    def test_parsed_level_fatal(self, parser):
        assert parser.extract_level("test", {"level": "FATAL"}) == "CRITICAL"

    def test_parsed_level_err(self, parser):
        assert parser.extract_level("test", {"level": "ERR"}) == "ERROR"

    def test_parsed_level_trace(self, parser):
        assert parser.extract_level("test", {"level": "TRACE"}) == "DEBUG"

    def test_parsed_level_unknown(self, parser):
        result = parser.extract_level("ERROR: something", {"level": "CUSTOM"})
        assert result == "ERROR"

    def test_no_parsed_fallback_to_content(self, parser):
        assert parser.extract_level("WARN: disk full") == "WARN"

    def test_no_level_defaults_info(self, parser):
        assert parser.extract_level("just a regular message") == "INFO"

    def test_parsed_level_none(self, parser):
        assert parser.extract_level("ERROR: crash", {"level": None}) == "ERROR"

    def test_earliest_level_wins(self, parser):
        assert parser.extract_level("INFO start then ERROR crash") == "INFO"


class TestParse:
    def test_falls_through_to_csv(self, parser):
        content = "level,message\nINFO,hello world"
        result = parser.parse(content)
        assert result["format"] == "csv"

    def test_falls_through_to_unstructured(self, parser):
        content = "just some random text"
        result = parser.parse(content)
        assert result["format"] == "unstructured"
        assert result["level"] == "INFO"

    def test_json_takes_priority(self, parser):
        content = '{"level": "ERROR", "message": "json wins"}'
        result = parser.parse(content)
        assert result["format"] == "json"

    def test_syslog_takes_priority_over_kv(self, parser):
        content = "<134>Jan  1 00:00:00 myhost myapp[1234]: level=INFO test"
        result = parser.parse(content)
        assert result["format"] == "syslog"

    def test_kv_takes_priority_over_csv(self, parser):
        content = 'level=INFO msg="test" service=api'
        result = parser.parse(content)
        assert result["format"] == "key_value"
