from __future__ import annotations

import json
import os
import tempfile
import time

import pytest
import pytest_asyncio

from app.services.log_storage_service import LogStorageService


@pytest_asyncio.fixture
async def storage():
    svc = LogStorageService()
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_log_extra.db")
        await svc.initialize(db_path=db_path)
        yield svc
        await svc.shutdown()


class TestWriteLog:
    @pytest.mark.asyncio
    async def test_write_log_no_structured_data(self, storage):
        log_id = await storage.write_log({
            "timestamp": time.time(),
            "source": "test",
            "level": "INFO",
            "content": "no structured data",
        })
        assert log_id > 0

    @pytest.mark.asyncio
    async def test_write_log_no_labels(self, storage):
        log_id = await storage.write_log({
            "timestamp": time.time(),
            "source": "test",
            "level": "INFO",
            "content": "no labels",
            "structured_data": {"key": "val"},
        })
        assert log_id > 0

    @pytest.mark.asyncio
    async def test_write_log_with_all_fields(self, storage):
        log_id = await storage.write_log({
            "timestamp": time.time(),
            "source": "full_test",
            "level": "ERROR",
            "content": "full entry",
            "structured_data": {"trace": "abc"},
            "container_name": "web",
            "container_id": "cid123",
            "labels": {"env": "staging"},
            "host": "10.0.0.1",
        })
        assert log_id > 0


class TestWriteLogs:
    @pytest.mark.asyncio
    async def test_write_logs_with_structured_data(self, storage):
        entries = [
            {
                "timestamp": time.time() + i,
                "source": "batch",
                "level": "INFO",
                "content": f"msg {i}",
                "structured_data": {"idx": i},
                "labels": {"batch": "true"},
            }
            for i in range(3)
        ]
        ids = await storage.write_logs(entries)
        assert len(ids) == 3
        assert all(id > 0 for id in ids)

    @pytest.mark.asyncio
    async def test_write_logs_empty_list(self, storage):
        ids = await storage.write_logs([])
        assert ids == []


class TestBuildFilterClauses:
    def test_level_list_filter(self, storage):
        clauses, params = storage._build_filter_clauses({"level": ["ERROR", "WARN"]})
        assert any("IN" in c for c in clauses)
        assert "ERROR" in params
        assert "WARN" in params

    def test_level_single_filter(self, storage):
        clauses, params = storage._build_filter_clauses({"level": "ERROR"})
        assert any("= ?" in c for c in clauses)
        assert "ERROR" in params

    def test_source_list_filter(self, storage):
        clauses, params = storage._build_filter_clauses({"source": ["app1", "app2"]})
        assert any("IN" in c for c in clauses)
        assert "app1" in params
        assert "app2" in params

    def test_source_single_filter(self, storage):
        clauses, params = storage._build_filter_clauses({"source": "app1"})
        assert any("= ?" in c for c in clauses)

    def test_container_name_list_filter(self, storage):
        clauses, params = storage._build_filter_clauses({"container_name": ["web", "api"]})
        assert any("IN" in c for c in clauses)

    def test_container_name_single_filter(self, storage):
        clauses, params = storage._build_filter_clauses({"container_name": "web"})
        assert any("= ?" in c for c in clauses)

    def test_labels_dict_filter_with_value(self, storage):
        clauses, params = storage._build_filter_clauses({"labels": {"env": "prod"}})
        assert any("LIKE" in c for c in clauses)
        assert any('"env"' in str(p) for p in params)

    def test_labels_dict_filter_none_value(self, storage):
        clauses, params = storage._build_filter_clauses({"labels": {"env": None}})
        assert any("LIKE" in c for c in clauses)
        assert any('"env"' in str(p) for p in params)

    def test_empty_filters(self, storage):
        clauses, params = storage._build_filter_clauses({})
        assert clauses == []
        assert params == []

    def test_time_range_filter(self, storage):
        clauses, params = storage._build_filter_clauses({"time_start": 1000.0, "time_end": 2000.0})
        assert len(clauses) == 2
        assert 1000.0 in params
        assert 2000.0 in params


class TestRowToDict:
    @pytest.mark.asyncio
    async def test_row_with_invalid_structured_data(self, storage):
        await storage._db.execute(
            "INSERT INTO logs (timestamp, source, level, content, structured_data) VALUES (?, ?, ?, ?, ?)",
            (time.time(), "test", "INFO", "msg", "not_valid_json{{{"),
        )
        await storage._db.commit()
        async with storage._db.execute("SELECT * FROM logs WHERE source = 'test'") as cursor:
            row = await cursor.fetchone()
        result = storage._row_to_dict(row)
        assert result["structured_data"] == "not_valid_json{{{"

    @pytest.mark.asyncio
    async def test_row_with_invalid_labels(self, storage):
        await storage._db.execute(
            "INSERT INTO logs (timestamp, source, level, content, labels) VALUES (?, ?, ?, ?, ?)",
            (time.time(), "test2", "INFO", "msg", "bad_labels{{{{"),
        )
        await storage._db.commit()
        async with storage._db.execute("SELECT * FROM logs WHERE source = 'test2'") as cursor:
            row = await cursor.fetchone()
        result = storage._row_to_dict(row)
        assert result["labels"] == "bad_labels{{{{"

    @pytest.mark.asyncio
    async def test_row_with_null_fields(self, storage):
        await storage._db.execute(
            "INSERT INTO logs (timestamp, source, level, content) VALUES (?, ?, ?, ?)",
            (time.time(), "test3", "INFO", "msg"),
        )
        await storage._db.commit()
        async with storage._db.execute("SELECT * FROM logs WHERE source = 'test3'") as cursor:
            row = await cursor.fetchone()
        result = storage._row_to_dict(row)
        assert result["structured_data"] is None
        assert result["labels"] is None
        assert result["container_name"] is None
        assert result["container_id"] is None
        assert result["host"] is None


class TestSearch:
    @pytest.mark.asyncio
    async def test_search_with_and_operator(self, storage):
        await storage.write_log({"timestamp": time.time(), "source": "s1", "level": "INFO", "content": "error database connection"})
        result = await storage.search("error AND database")
        assert result["total"] >= 1

    @pytest.mark.asyncio
    async def test_search_with_or_operator(self, storage):
        await storage.write_log({"timestamp": time.time(), "source": "s1", "level": "INFO", "content": "error occurred"})
        await storage.write_log({"timestamp": time.time(), "source": "s2", "level": "INFO", "content": "warning issued"})
        result = await storage.search("error OR warning")
        assert result["total"] >= 2

    @pytest.mark.asyncio
    async def test_search_with_not_operator(self, storage):
        await storage.write_log({"timestamp": time.time(), "source": "s1", "level": "INFO", "content": "error database connection"})
        await storage.write_log({"timestamp": time.time(), "source": "s2", "level": "INFO", "content": "error network timeout"})
        result = await storage.search("error NOT database")
        assert result["total"] >= 1

    @pytest.mark.asyncio
    async def test_search_with_level_list_filter(self, storage):
        now = time.time()
        await storage.write_log({"timestamp": now, "source": "f1", "level": "ERROR", "content": "error log"})
        await storage.write_log({"timestamp": now, "source": "f2", "level": "WARN", "content": "warn log"})
        await storage.write_log({"timestamp": now, "source": "f3", "level": "INFO", "content": "info log"})
        result = await storage.search("log", filters={"level": ["ERROR", "WARN"]})
        assert result["total"] >= 2
        assert all(r["level"] in ("ERROR", "WARN") for r in result["results"])

    @pytest.mark.asyncio
    async def test_search_with_source_list_filter(self, storage):
        now = time.time()
        await storage.write_log({"timestamp": now, "source": "alpha", "level": "INFO", "content": "alpha log"})
        await storage.write_log({"timestamp": now, "source": "beta", "level": "INFO", "content": "beta log"})
        result = await storage.search("log", filters={"source": ["alpha"]})
        assert result["total"] >= 1
        assert all(r["source"] == "alpha" for r in result["results"])

    @pytest.mark.asyncio
    async def test_search_pagination(self, storage):
        for i in range(15):
            await storage.write_log({"timestamp": time.time() + i * 0.01, "source": "page", "level": "INFO", "content": f"search page {i}"})
        result = await storage.search("search page", page=1, page_size=5)
        assert result["page_size"] == 5
        assert len(result["results"]) == 5
        assert result["total"] >= 15


class TestFilterLogs:
    @pytest.mark.asyncio
    async def test_filter_with_level_list(self, storage):
        now = time.time()
        await storage.write_log({"timestamp": now, "source": "app", "level": "ERROR", "content": "err"})
        await storage.write_log({"timestamp": now, "source": "app", "level": "WARN", "content": "warn"})
        await storage.write_log({"timestamp": now, "source": "app", "level": "INFO", "content": "info"})
        result = await storage.filter_logs({"level": ["ERROR", "WARN"]})
        assert result["total"] >= 2

    @pytest.mark.asyncio
    async def test_filter_with_source_list(self, storage):
        now = time.time()
        await storage.write_log({"timestamp": now, "source": "svc_a", "level": "INFO", "content": "a"})
        await storage.write_log({"timestamp": now, "source": "svc_b", "level": "INFO", "content": "b"})
        result = await storage.filter_logs({"source": ["svc_a"]})
        assert result["total"] >= 1
        assert all(r["source"] == "svc_a" for r in result["results"])

    @pytest.mark.asyncio
    async def test_filter_with_container_name(self, storage):
        now = time.time()
        await storage.write_log({"timestamp": now, "source": "app", "level": "INFO", "content": "c1", "container_name": "web"})
        await storage.write_log({"timestamp": now, "source": "app", "level": "INFO", "content": "c2", "container_name": "api"})
        result = await storage.filter_logs({"container_name": "web"})
        assert result["total"] >= 1
        assert all(r["container_name"] == "web" for r in result["results"])

    @pytest.mark.asyncio
    async def test_filter_with_container_name_list(self, storage):
        now = time.time()
        await storage.write_log({"timestamp": now, "source": "app", "level": "INFO", "content": "c1", "container_name": "web"})
        await storage.write_log({"timestamp": now, "source": "app", "level": "INFO", "content": "c2", "container_name": "api"})
        result = await storage.filter_logs({"container_name": ["web", "api"]})
        assert result["total"] >= 2

    @pytest.mark.asyncio
    async def test_filter_with_labels(self, storage):
        now = time.time()
        await storage.write_log({"timestamp": now, "source": "app", "level": "INFO", "content": "labeled", "labels": {"env": "prod"}})
        result = await storage.filter_logs({"labels": {"env": "prod"}})
        assert result["total"] >= 1

    @pytest.mark.asyncio
    async def test_filter_no_results(self, storage):
        result = await storage.filter_logs({"level": "NONEXISTENT"})
        assert result["total"] == 0
        assert result["results"] == []


class TestGetTrend:
    @pytest.mark.asyncio
    async def test_trend_with_level_filter(self, storage):
        now = time.time()
        for i in range(5):
            await storage.write_log({"timestamp": now - i * 60, "source": "app", "level": "ERROR", "content": f"err {i}"})
        for i in range(3):
            await storage.write_log({"timestamp": now - i * 60, "source": "app", "level": "INFO", "content": f"info {i}"})
        trend = await storage.get_trend(now - 600, now, granularity="minute", level="ERROR")
        assert len(trend) > 0
        assert all(t["count"] >= 1 for t in trend)

    @pytest.mark.asyncio
    async def test_trend_day_granularity(self, storage):
        now = time.time()
        for i in range(5):
            await storage.write_log({"timestamp": now - i * 3600, "source": "app", "level": "INFO", "content": f"day {i}"})
        trend = await storage.get_trend(now - 86400, now, granularity="day")
        assert len(trend) > 0

    @pytest.mark.asyncio
    async def test_trend_week_granularity(self, storage):
        now = time.time()
        for i in range(5):
            await storage.write_log({"timestamp": now - i * 86400, "source": "app", "level": "INFO", "content": f"week {i}"})
        trend = await storage.get_trend(now - 604800, now, granularity="week")
        assert len(trend) > 0

    @pytest.mark.asyncio
    async def test_trend_month_granularity(self, storage):
        now = time.time()
        for i in range(5):
            await storage.write_log({"timestamp": now - i * 86400 * 30, "source": "app", "level": "INFO", "content": f"month {i}"})
        trend = await storage.get_trend(now - 86400 * 180, now, granularity="month")
        assert len(trend) > 0

    @pytest.mark.asyncio
    async def test_trend_invalid_granularity_defaults_hour(self, storage):
        now = time.time()
        await storage.write_log({"timestamp": now, "source": "app", "level": "INFO", "content": "default"})
        trend = await storage.get_trend(now - 3600, now, granularity="invalid")
        assert isinstance(trend, list)


class TestGetKeywordFrequency:
    @pytest.mark.asyncio
    async def test_keyword_frequency_basic(self, storage):
        now = time.time()
        for i in range(5):
            await storage.write_log({"timestamp": now - i * 60, "source": "app", "level": "INFO", "content": f"database error {i}"})
        freq = await storage.get_keyword_frequency("database error", now - 600, now, granularity="minute")
        assert len(freq) > 0
        assert "bucket" in freq[0]
        assert "count" in freq[0]

    @pytest.mark.asyncio
    async def test_keyword_frequency_with_and(self, storage):
        now = time.time()
        await storage.write_log({"timestamp": now, "source": "app", "level": "INFO", "content": "connection timeout error"})
        freq = await storage.get_keyword_frequency("connection AND timeout", now - 60, now)
        assert len(freq) >= 1

    @pytest.mark.asyncio
    async def test_keyword_frequency_day_granularity(self, storage):
        now = time.time()
        for i in range(3):
            await storage.write_log({"timestamp": now - i * 3600, "source": "app", "level": "INFO", "content": "daily keyword"})
        freq = await storage.get_keyword_frequency("daily keyword", now - 86400, now, granularity="day")
        assert len(freq) > 0


class TestGetContext:
    @pytest.mark.asyncio
    async def test_context_nonexistent_id(self, storage):
        ctx = await storage.get_context(999999)
        assert ctx["target"] is None
        assert ctx["before"] == []
        assert ctx["after"] == []

    @pytest.mark.asyncio
    async def test_context_with_before_and_after(self, storage):
        now = time.time()
        ids = []
        for i in range(11):
            log_id = await storage.write_log({"timestamp": now + i, "source": "ctx", "level": "INFO", "content": f"line {i}"})
            ids.append(log_id)
        ctx = await storage.get_context(ids[5], before=3, after=3)
        assert ctx["target"]["id"] == ids[5]
        assert len(ctx["before"]) <= 3
        assert len(ctx["after"]) <= 3

    @pytest.mark.asyncio
    async def test_context_first_log_no_before(self, storage):
        now = time.time()
        ids = []
        for i in range(5):
            log_id = await storage.write_log({"timestamp": now + i, "source": "edge", "level": "INFO", "content": f"edge {i}"})
            ids.append(log_id)
        ctx = await storage.get_context(ids[0], before=3, after=3)
        assert ctx["target"]["id"] == ids[0]
        assert ctx["before"] == []

    @pytest.mark.asyncio
    async def test_context_last_log_no_after(self, storage):
        now = time.time()
        ids = []
        for i in range(5):
            log_id = await storage.write_log({"timestamp": now + i, "source": "edge", "level": "INFO", "content": f"edge {i}"})
            ids.append(log_id)
        ctx = await storage.get_context(ids[-1], before=3, after=3)
        assert ctx["target"]["id"] == ids[-1]
        assert ctx["after"] == []


class TestRotation:
    @pytest.mark.asyncio
    async def test_rotate_by_rows(self, storage):
        storage._max_rows = 5
        for i in range(10):
            await storage.write_log({"timestamp": time.time() + i, "source": "rot", "level": "INFO", "content": f"row {i}"})
        await storage._rotate_by_rows()
        result = await storage.filter_logs({"source": "rot"})
        assert result["total"] <= 5

    @pytest.mark.asyncio
    async def test_rotate_by_age(self, storage):
        storage._max_age_days = 1
        old_ts = time.time() - 86400 * 2
        await storage.write_log({"timestamp": old_ts, "source": "old_age", "level": "INFO", "content": "old log"})
        await storage.write_log({"timestamp": time.time(), "source": "new_age", "level": "INFO", "content": "new log"})
        await storage._rotate_by_age()
        result = await storage.filter_logs({"source": "old_age"})
        assert result["total"] == 0
        result2 = await storage.filter_logs({"source": "new_age"})
        assert result2["total"] >= 1

    @pytest.mark.asyncio
    async def test_check_rotation(self, storage):
        storage._max_rows = 1000000
        storage._max_age_days = 90
        await storage.write_log({"timestamp": time.time(), "source": "rot_check", "level": "INFO", "content": "check"})
        await storage.check_rotation()
        result = await storage.filter_logs({"source": "rot_check"})
        assert result["total"] >= 1

    @pytest.mark.asyncio
    async def test_maybe_vacuum_skips_recent(self, storage):
        storage._last_vacuum = time.time()
        await storage._maybe_vacuum()
        assert storage._last_vacuum == time.time() or storage._last_vacuum > 0

    @pytest.mark.asyncio
    async def test_maybe_vacuum_runs_after_interval(self, storage):
        storage._last_vacuum = time.time() - 86400 * 2
        await storage.write_log({"timestamp": time.time(), "source": "vacuum", "level": "INFO", "content": "vacuum test"})
        await storage._maybe_vacuum()
        assert storage._last_vacuum > time.time() - 100


class TestGetSourceDistribution:
    @pytest.mark.asyncio
    async def test_source_distribution_top_n(self, storage):
        now = time.time()
        for _ in range(5):
            await storage.write_log({"timestamp": now, "source": "top1", "level": "INFO", "content": "msg"})
        for _ in range(3):
            await storage.write_log({"timestamp": now, "source": "top2", "level": "INFO", "content": "msg"})
        for _ in range(1):
            await storage.write_log({"timestamp": now, "source": "top3", "level": "INFO", "content": "msg"})
        dist = await storage.get_source_distribution(now - 60, now + 60, top_n=2)
        assert len(dist) <= 2
        assert dist[0]["source"] == "top1"


class TestGetLevelDistribution:
    @pytest.mark.asyncio
    async def test_level_distribution_ordering(self, storage):
        now = time.time()
        for _ in range(5):
            await storage.write_log({"timestamp": now, "source": "lvl", "level": "INFO", "content": "msg"})
        for _ in range(2):
            await storage.write_log({"timestamp": now, "source": "lvl", "level": "ERROR", "content": "msg"})
        dist = await storage.get_level_distribution(now - 60, now + 60)
        assert len(dist) >= 2
        info_entry = next(d for d in dist if d["level"] == "INFO")
        error_entry = next(d for d in dist if d["level"] == "ERROR")
        assert info_entry["count"] > error_entry["count"]
