from __future__ import annotations

import csv
import io
import json
import re
import time
from datetime import datetime, timezone
from typing import Any, Optional


_LEVEL_KEYWORDS = [
    (re.compile(r'\bCRITICAL\b', re.IGNORECASE), "CRITICAL"),
    (re.compile(r'\bFATAL\b', re.IGNORECASE), "CRITICAL"),
    (re.compile(r'\bERROR\b', re.IGNORECASE), "ERROR"),
    (re.compile(r'\bERR\b', re.IGNORECASE), "ERROR"),
    (re.compile(r'\bWARN\b', re.IGNORECASE), "WARN"),
    (re.compile(r'\bWARNING\b', re.IGNORECASE), "WARN"),
    (re.compile(r'\bINFO\b', re.IGNORECASE), "INFO"),
    (re.compile(r'\bDEBUG\b', re.IGNORECASE), "DEBUG"),
    (re.compile(r'\bTRACE\b', re.IGNORECASE), "DEBUG"),
]

_LEVEL_NORMALIZE: dict[str, str] = {
    "CRITICAL": "CRITICAL",
    "FATAL": "CRITICAL",
    "ERROR": "ERROR",
    "ERR": "ERROR",
    "WARN": "WARN",
    "WARNING": "WARN",
    "INFO": "INFO",
    "DEBUG": "DEBUG",
    "TRACE": "DEBUG",
}

_SYSLOG_SEVERITY_MAP: dict[int, str] = {
    0: "CRITICAL",
    1: "CRITICAL",
    2: "CRITICAL",
    3: "ERROR",
    4: "WARN",
    5: "INFO",
    6: "INFO",
    7: "DEBUG",
}

_TIMESTAMP_FORMATS = [
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S.%f",
    "%d/%b/%Y:%H:%M:%S",
    "%b %d %H:%M:%S",
    "%b  %d %H:%M:%S",
]

_SYSLOG_RFC3164_RE = re.compile(
    r'^<(?P<pri>\d{1,3})>'
    r'(?P<timestamp>[A-Z][a-z]{2}\s{1,2}\d{1,2}\s\d{2}:\d{2}:\d{2})\s+'
    r'(?P<hostname>\S+)\s+'
    r'(?P<app_name>\S+?)(?:\[(?P<proc_id>\d+)\])?:\s*'
    r'(?P<message>.*)$'
)

_SYSLOG_RFC5424_RE = re.compile(
    r'^<(?P<pri>\d{1,3})>'
    r'(?P<version>\d+)\s+'
    r'(?P<timestamp>\S+)\s+'
    r'(?P<hostname>\S+)\s+'
    r'(?P<app_name>\S+)\s+'
    r'(?P<proc_id>\S+)\s+'
    r'(?P<msgid>\S+)\s+'
    r'(?P<structured_data>(?:\[.*?\])+|-)\s*'
    r'(?P<message>.*)$'
)

_KV_RE = re.compile(
    r'(?P<key>\w[\w.-]*)'
    r'(?:=|:\s*)'
    r'(?P<value>"[^"]*"|\'[^\']*\'|\S+)'
)


class LogParserService:

    def parse_timestamp(self, ts_str: str) -> float | None:
        if not ts_str or not ts_str.strip():
            return None
        ts_str = ts_str.strip()
        try:
            val = float(ts_str)
            if val > 0:
                return val
        except ValueError:
            pass
        for fmt in _TIMESTAMP_FORMATS:
            try:
                dt = datetime.strptime(ts_str, fmt)
                if fmt in ("%b %d %H:%M:%S", "%b  %d %H:%M:%S"):
                    now = datetime.now()
                    dt = dt.replace(year=now.year, tzinfo=None)
                return dt.timestamp()
            except ValueError:
                continue
        iso_variants = [ts_str]
        if "+" in ts_str and "T" in ts_str:
            iso_variants.append(ts_str.split("+")[0])
            iso_variants.append(ts_str.split("+")[0].rstrip("Z"))
        if ts_str.endswith("Z"):
            iso_variants.append(ts_str[:-1])
        for variant in iso_variants:
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
                try:
                    dt = datetime.strptime(variant, fmt)
                    return dt.replace(tzinfo=timezone.utc).timestamp()
                except ValueError:
                    continue
        return None

    def parse_json(self, content: str) -> dict | None:
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, ValueError):
            return None
        if not isinstance(data, dict):
            return None
        level = None
        for key in ("level", "log_level", "severity", "lvl"):
            if key in data:
                raw = str(data[key]).strip().upper()
                level = _LEVEL_NORMALIZE.get(raw)
                if level is None:
                    for norm_key, norm_val in _LEVEL_NORMALIZE.items():
                        if norm_key in raw:
                            level = norm_val
                            break
                if level is not None:
                    break
        timestamp = None
        for key in ("timestamp", "time", "ts", "datetime", "date", "@timestamp"):
            if key in data:
                timestamp = self.parse_timestamp(str(data[key]))
                if timestamp is not None:
                    break
        message = ""
        for key in ("message", "msg", "text", "log"):
            if key in data:
                message = str(data[key])
                break
        skip_keys = {
            "level", "log_level", "severity", "lvl",
            "timestamp", "time", "ts", "datetime", "date", "@timestamp",
            "message", "msg", "text", "log",
        }
        fields = {k: v for k, v in data.items() if k not in skip_keys}
        return {
            "format": "json",
            "level": level,
            "timestamp": timestamp,
            "fields": fields,
            "message": message,
        }

    def parse_key_value(self, content: str) -> dict | None:
        pairs = _KV_RE.findall(content)
        if not pairs:
            return None
        if len(pairs) < 2:
            return None
        fields: dict[str, Any] = {}
        for key, value in pairs:
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            fields[key] = value
        level = None
        for key in ("level", "log_level", "severity", "lvl"):
            if key in fields:
                raw = str(fields[key]).strip().upper()
                level = _LEVEL_NORMALIZE.get(raw)
                if level is None:
                    for norm_key, norm_val in _LEVEL_NORMALIZE.items():
                        if norm_key in raw:
                            level = norm_val
                            break
                if level is not None:
                    break
        timestamp = None
        for key in ("timestamp", "time", "ts", "datetime", "date"):
            if key in fields:
                timestamp = self.parse_timestamp(str(fields[key]))
                if timestamp is not None:
                    break
        skip_keys = {"level", "log_level", "severity", "lvl", "timestamp", "time", "ts", "datetime", "date"}
        clean_fields = {k: v for k, v in fields.items() if k not in skip_keys}
        message = ""
        remaining = content
        for key, _ in pairs:
            remaining = remaining.replace(key, "", 1)
        remaining = re.sub(r'[\s=:"\']+', ' ', remaining).strip()
        if remaining:
            message = remaining
        return {
            "format": "key_value",
            "level": level,
            "timestamp": timestamp,
            "fields": clean_fields,
            "message": message,
        }

    def parse_syslog(self, content: str) -> dict | None:
        m = _SYSLOG_RFC5424_RE.match(content)
        if m:
            pri = int(m.group("pri"))
            facility = pri // 8
            severity = pri % 8
            level = _SYSLOG_SEVERITY_MAP.get(severity)
            timestamp = self.parse_timestamp(m.group("timestamp"))
            hostname = m.group("hostname")
            if hostname == "-":
                hostname = None
            app_name = m.group("app_name")
            if app_name == "-":
                app_name = None
            proc_id = m.group("proc_id")
            if proc_id == "-":
                proc_id = None
            msgid = m.group("msgid")
            if msgid == "-":
                msgid = None
            structured_data = m.group("structured_data")
            fields: dict[str, Any] = {
                "facility": facility,
                "severity": severity,
                "hostname": hostname,
                "app_name": app_name,
                "proc_id": proc_id,
            }
            if msgid is not None:
                fields["msgid"] = msgid
            if structured_data and structured_data != "-":
                fields["structured_data"] = structured_data
            return {
                "format": "syslog",
                "level": level,
                "timestamp": timestamp,
                "fields": fields,
                "message": m.group("message"),
            }
        m = _SYSLOG_RFC3164_RE.match(content)
        if m:
            pri = int(m.group("pri"))
            facility = pri // 8
            severity = pri % 8
            level = _SYSLOG_SEVERITY_MAP.get(severity)
            timestamp = self.parse_timestamp(m.group("timestamp"))
            hostname = m.group("hostname")
            app_name = m.group("app_name")
            proc_id = m.group("proc_id")
            fields = {
                "facility": facility,
                "severity": severity,
                "hostname": hostname,
                "app_name": app_name,
                "proc_id": proc_id,
            }
            return {
                "format": "syslog",
                "level": level,
                "timestamp": timestamp,
                "fields": fields,
                "message": m.group("message"),
            }
        return None

    def parse_csv(self, content: str) -> dict | None:
        lines = content.strip().splitlines()
        if len(lines) < 2:
            return None
        try:
            reader = csv.reader(io.StringIO(content))
            rows = list(reader)
        except csv.Error:
            return None
        if not rows or len(rows) < 2:
            return None
        header = rows[0]
        first_data = rows[1]
        if len(first_data) != len(header):
            return None
        fields: dict[str, Any] = {}
        for i, col_name in enumerate(header):
            if i < len(first_data):
                fields[col_name.strip()] = first_data[i].strip()
        level = None
        for key in ("level", "log_level", "severity", "lvl"):
            if key in fields:
                raw = str(fields[key]).strip().upper()
                level = _LEVEL_NORMALIZE.get(raw)
                if level is None:
                    for norm_key, norm_val in _LEVEL_NORMALIZE.items():
                        if norm_key in raw:
                            level = norm_val
                            break
                if level is not None:
                    break
        timestamp = None
        for key in ("timestamp", "time", "ts", "datetime", "date"):
            if key in fields:
                timestamp = self.parse_timestamp(str(fields[key]))
                if timestamp is not None:
                    break
        skip_keys = {"level", "log_level", "severity", "lvl", "timestamp", "time", "ts", "datetime", "date"}
        clean_fields = {k: v for k, v in fields.items() if k not in skip_keys}
        message = ""
        for key in ("message", "msg", "text", "log"):
            if key in fields:
                message = str(fields[key])
                break
        if not message:
            message = " | ".join(v for v in first_data if v.strip())
        return {
            "format": "csv",
            "level": level,
            "timestamp": timestamp,
            "fields": clean_fields,
            "message": message,
        }

    def extract_level(self, content: str, parsed: dict | None = None) -> str:
        if parsed is not None:
            parsed_level = parsed.get("level")
            if parsed_level and parsed_level in ("DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"):
                return parsed_level
            if parsed_level:
                raw = str(parsed_level).strip().upper()
                normalized = _LEVEL_NORMALIZE.get(raw)
                if normalized:
                    return normalized
        best_pos = len(content) + 1
        best_level = None
        for pattern, level in _LEVEL_KEYWORDS:
            m = pattern.search(content)
            if m and m.start() < best_pos:
                best_pos = m.start()
                best_level = level
        if best_level is not None:
            return best_level
        return "INFO"

    def parse(self, content: str) -> dict:
        result = None
        result = self.parse_json(content)
        if result is None:
            result = self.parse_syslog(content)
        if result is None:
            result = self.parse_key_value(content)
        if result is None:
            result = self.parse_csv(content)
        if result is None:
            return {
                "format": "unstructured",
                "level": self.extract_level(content),
                "timestamp": None,
                "fields": {},
                "message": content,
            }
        result["level"] = self.extract_level(content, result)
        return result


log_parser_service = LogParserService()
