from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Optional

import aiosqlite


class LogStorageService:
    DEFAULT_DB_PATH = "data/log_analysis.db"
    DEFAULT_MAX_SIZE_MB = 500
    DEFAULT_MAX_ROWS = 5_000_000
    DEFAULT_MAX_AGE_DAYS = 90
    VACUUM_INTERVAL = 86400

    def __init__(self):
        self._db: Optional[aiosqlite.Connection] = None
        self._db_path: Optional[str] = None
        self._max_size_mb: int = self.DEFAULT_MAX_SIZE_MB
        self._max_rows: int = self.DEFAULT_MAX_ROWS
        self._max_age_days: int = self.DEFAULT_MAX_AGE_DAYS
        self._last_vacuum: float = 0.0

    async def initialize(self, db_path: str = None) -> None:
        if db_path is None:
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            db_path = str(project_root / self.DEFAULT_DB_PATH)
        self._db_path = db_path

        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        self._db = await aiosqlite.connect(db_path)
        self._db.row_factory = aiosqlite.Row

        await self._create_tables()

    async def _create_tables(self) -> None:
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                source TEXT NOT NULL,
                level TEXT NOT NULL,
                content TEXT NOT NULL,
                structured_data TEXT,
                container_name TEXT,
                container_id TEXT,
                labels TEXT,
                host TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp);
            CREATE INDEX IF NOT EXISTS idx_logs_source ON logs(source);
            CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level);
            CREATE INDEX IF NOT EXISTS idx_logs_container_name ON logs(container_name);
            CREATE INDEX IF NOT EXISTS idx_logs_host ON logs(host);

            CREATE VIRTUAL TABLE IF NOT EXISTS logs_fts USING fts5(
                content,
                content='logs',
                content_rowid='id'
            );

            CREATE TRIGGER IF NOT EXISTS logs_ai AFTER INSERT ON logs BEGIN
                INSERT INTO logs_fts(rowid, content) VALUES (new.id, new.content);
            END;

            CREATE TRIGGER IF NOT EXISTS logs_ad AFTER DELETE ON logs BEGIN
                INSERT INTO logs_fts(logs_fts, rowid, content) VALUES('delete', old.id, old.content);
            END;

            CREATE TRIGGER IF NOT EXISTS logs_au AFTER UPDATE ON logs BEGIN
                INSERT INTO logs_fts(logs_fts, rowid, content) VALUES('delete', old.id, old.content);
                INSERT INTO logs_fts(rowid, content) VALUES (new.id, new.content);
            END;

            CREATE TABLE IF NOT EXISTS alert_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                pattern TEXT NOT NULL,
                pattern_type TEXT NOT NULL DEFAULT 'keyword',
                time_window INTEGER NOT NULL DEFAULT 300,
                threshold INTEGER NOT NULL DEFAULT 1,
                enabled INTEGER NOT NULL DEFAULT 1,
                silence_period INTEGER NOT NULL DEFAULT 3600,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS alert_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id INTEGER NOT NULL,
                triggered_at REAL NOT NULL,
                match_count INTEGER NOT NULL DEFAULT 0,
                notified INTEGER NOT NULL DEFAULT 0,
                detail TEXT,
                FOREIGN KEY (rule_id) REFERENCES alert_rules(id)
            );

            CREATE INDEX IF NOT EXISTS idx_alert_events_rule_id ON alert_events(rule_id);
            CREATE INDEX IF NOT EXISTS idx_alert_events_triggered_at ON alert_events(triggered_at);
        """)
        await self._db.commit()

    async def shutdown(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None

    async def write_log(self, log_entry: dict) -> int:
        cursor = await self._db.execute(
            """
            INSERT INTO logs (timestamp, source, level, content, structured_data,
                              container_name, container_id, labels, host)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log_entry.get("timestamp", time.time()),
                log_entry.get("source", ""),
                log_entry.get("level", "info"),
                log_entry.get("content", ""),
                json.dumps(log_entry.get("structured_data"), ensure_ascii=False)
                if log_entry.get("structured_data") is not None
                else None,
                log_entry.get("container_name"),
                log_entry.get("container_id"),
                json.dumps(log_entry.get("labels"), ensure_ascii=False)
                if log_entry.get("labels") is not None
                else None,
                log_entry.get("host"),
            ),
        )
        await self._db.commit()
        return cursor.lastrowid

    async def write_logs(self, log_entries: list[dict]) -> list[int]:
        ids = []
        await self._db.execute("BEGIN")
        for entry in log_entries:
            cursor = await self._db.execute(
                """
                INSERT INTO logs (timestamp, source, level, content, structured_data,
                                  container_name, container_id, labels, host)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.get("timestamp", time.time()),
                    entry.get("source", ""),
                    entry.get("level", "info"),
                    entry.get("content", ""),
                    json.dumps(entry.get("structured_data"), ensure_ascii=False)
                    if entry.get("structured_data") is not None
                    else None,
                    entry.get("container_name"),
                    entry.get("container_id"),
                    json.dumps(entry.get("labels"), ensure_ascii=False)
                    if entry.get("labels") is not None
                    else None,
                    entry.get("host"),
                ),
            )
            ids.append(cursor.lastrowid)
        await self._db.commit()
        return ids

    def _build_filter_clauses(self, filters: dict) -> tuple[list[str], list[Any]]:
        clauses = []
        params = []

        if filters.get("time_start") is not None:
            clauses.append("timestamp >= ?")
            params.append(filters["time_start"])
        if filters.get("time_end") is not None:
            clauses.append("timestamp <= ?")
            params.append(filters["time_end"])
        if filters.get("level") is not None:
            if isinstance(filters["level"], list):
                placeholders = ",".join("?" for _ in filters["level"])
                clauses.append(f"level IN ({placeholders})")
                params.extend(filters["level"])
            else:
                clauses.append("level = ?")
                params.append(filters["level"])
        if filters.get("source") is not None:
            if isinstance(filters["source"], list):
                placeholders = ",".join("?" for _ in filters["source"])
                clauses.append(f"source IN ({placeholders})")
                params.extend(filters["source"])
            else:
                clauses.append("source = ?")
                params.append(filters["source"])
        if filters.get("container_name") is not None:
            if isinstance(filters["container_name"], list):
                placeholders = ",".join("?" for _ in filters["container_name"])
                clauses.append(f"container_name IN ({placeholders})")
                params.extend(filters["container_name"])
            else:
                clauses.append("container_name = ?")
                params.append(filters["container_name"])
        if filters.get("labels") is not None and isinstance(filters["labels"], dict):
            for key, value in filters["labels"].items():
                clauses.append("labels LIKE ?")
                if value is None:
                    params.append(f'%"{key}"%')
                else:
                    params.append(f'%"{key}":%"{value}"%')

        return clauses, params

    async def search(
        self,
        query: str,
        filters: dict = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        if filters is None:
            filters = {}

        fts_query = query
        if not re.search(r'\b(AND|OR|NOT)\b', fts_query, re.IGNORECASE):
            fts_query = " AND ".join(re.findall(r'\S+', fts_query))

        count_sql = """
            SELECT COUNT(*)
            FROM logs_fts fts
            JOIN logs l ON l.id = fts.rowid
            WHERE fts.logs_fts MATCH ?
        """
        data_sql = """
            SELECT l.id, l.timestamp, l.source, l.level, l.content,
                   l.structured_data, l.container_name, l.container_id,
                   l.labels, l.host
            FROM logs_fts fts
            JOIN logs l ON l.id = fts.rowid
            WHERE fts.logs_fts MATCH ?
        """

        clauses, params = self._build_filter_clauses(filters)
        where_ext = ""
        if clauses:
            where_ext = " AND " + " AND ".join(clauses)

        count_sql += where_ext
        data_sql += where_ext

        count_params = [fts_query] + params
        data_params = [fts_query] + params

        offset = (page - 1) * page_size
        data_sql += " ORDER BY l.timestamp DESC LIMIT ? OFFSET ?"
        data_params.extend([page_size, offset])

        async with self._db.execute(count_sql, count_params) as cursor:
            row = await cursor.fetchone()
            total = row[0]

        results = []
        async with self._db.execute(data_sql, data_params) as cursor:
            rows = await cursor.fetchall()
            for r in rows:
                results.append(self._row_to_dict(r))

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": results,
        }

    async def filter_logs(
        self,
        filters: dict,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        clauses, params = self._build_filter_clauses(filters)

        where = ""
        if clauses:
            where = "WHERE " + " AND ".join(clauses)

        count_sql = f"SELECT COUNT(*) FROM logs {where}"
        data_sql = f"""
            SELECT id, timestamp, source, level, content,
                   structured_data, container_name, container_id, labels, host
            FROM logs
            {where}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """

        async with self._db.execute(count_sql, params) as cursor:
            row = await cursor.fetchone()
            total = row[0]

        offset = (page - 1) * page_size
        data_params = params + [page_size, offset]

        results = []
        async with self._db.execute(data_sql, data_params) as cursor:
            rows = await cursor.fetchall()
            for r in rows:
                results.append(self._row_to_dict(r))

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": results,
        }

    def _row_to_dict(self, row: aiosqlite.Row) -> dict:
        structured_data = row["structured_data"]
        if structured_data is not None:
            try:
                structured_data = json.loads(structured_data)
            except (json.JSONDecodeError, TypeError):
                pass

        labels = row["labels"]
        if labels is not None:
            try:
                labels = json.loads(labels)
            except (json.JSONDecodeError, TypeError):
                pass

        return {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "source": row["source"],
            "level": row["level"],
            "content": row["content"],
            "structured_data": structured_data,
            "container_name": row["container_name"],
            "container_id": row["container_id"],
            "labels": labels,
            "host": row["host"],
        }

    async def check_rotation(self) -> None:
        await self._rotate_by_size()
        await self._rotate_by_rows()
        await self._rotate_by_age()
        await self._maybe_vacuum()

    async def _rotate_by_size(self) -> None:
        db_file = Path(self._db_path)
        if not db_file.exists():
            return
        size_mb = db_file.stat().st_size / (1024 * 1024)
        if size_mb > self._max_size_mb:
            cutoff = time.time() - (self._max_age_days * 86400)
            await self._db.execute(
                "DELETE FROM logs WHERE timestamp < ?", (cutoff,)
            )
            await self._db.commit()

    async def _rotate_by_rows(self) -> None:
        async with self._db.execute("SELECT COUNT(*) FROM logs") as cursor:
            row = await cursor.fetchone()
            count = row[0]

        if count > self._max_rows:
            delete_count = count - self._max_rows
            await self._db.execute(
                """
                DELETE FROM logs WHERE id IN (
                    SELECT id FROM logs ORDER BY timestamp ASC LIMIT ?
                )
                """,
                (delete_count,),
            )
            await self._db.commit()

    async def _rotate_by_age(self) -> None:
        cutoff = time.time() - (self._max_age_days * 86400)
        await self._db.execute("DELETE FROM logs WHERE timestamp < ?", (cutoff,))
        await self._db.commit()

    async def _maybe_vacuum(self) -> None:
        now = time.time()
        if now - self._last_vacuum < self.VACUUM_INTERVAL:
            return
        await self._db.execute("INSERT INTO logs_fts(logs_fts) VALUES('optimize')")
        await self._db.commit()
        await self._db.execute("VACUUM")
        self._last_vacuum = now

    async def get_trend(
        self,
        time_start: float,
        time_end: float,
        granularity: str = "hour",
        level: str = None,
    ) -> list[dict]:
        granularity_map = {
            "minute": "%Y-%m-%d %H:%M",
            "hour": "%Y-%m-%d %H:00",
            "day": "%Y-%m-%d",
            "week": "%Y-W%W",
            "month": "%Y-%m",
        }
        fmt = granularity_map.get(granularity, "%Y-%m-%d %H:00")

        params: list[Any] = [time_start, time_end]
        level_clause = ""
        if level is not None:
            level_clause = " AND level = ?"
            params.append(level)

        sql = f"""
            SELECT strftime('{fmt}', timestamp, 'unixepoch', 'localtime') AS bucket,
                   COUNT(*) AS count
            FROM logs
            WHERE timestamp >= ? AND timestamp <= ?{level_clause}
            GROUP BY bucket
            ORDER BY bucket
        """

        results = []
        async with self._db.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
            for r in rows:
                results.append({"bucket": r[0], "count": r[1]})

        return results

    async def get_source_distribution(
        self,
        time_start: float,
        time_end: float,
        top_n: int = 10,
    ) -> list[dict]:
        sql = """
            SELECT source, COUNT(*) AS count
            FROM logs
            WHERE timestamp >= ? AND timestamp <= ?
            GROUP BY source
            ORDER BY count DESC
            LIMIT ?
        """
        results = []
        async with self._db.execute(sql, (time_start, time_end, top_n)) as cursor:
            rows = await cursor.fetchall()
            for r in rows:
                results.append({"source": r[0], "count": r[1]})

        return results

    async def get_level_distribution(
        self,
        time_start: float,
        time_end: float,
    ) -> list[dict]:
        sql = """
            SELECT level, COUNT(*) AS count
            FROM logs
            WHERE timestamp >= ? AND timestamp <= ?
            GROUP BY level
            ORDER BY count DESC
        """
        results = []
        async with self._db.execute(sql, (time_start, time_end)) as cursor:
            rows = await cursor.fetchall()
            for r in rows:
                results.append({"level": r[0], "count": r[1]})

        return results

    async def get_keyword_frequency(
        self,
        keyword: str,
        time_start: float,
        time_end: float,
        granularity: str = "hour",
    ) -> list[dict]:
        granularity_map = {
            "minute": "%Y-%m-%d %H:%M",
            "hour": "%Y-%m-%d %H:00",
            "day": "%Y-%m-%d",
            "week": "%Y-W%W",
            "month": "%Y-%m",
        }
        fmt = granularity_map.get(granularity, "%Y-%m-%d %H:00")

        fts_query = keyword
        if not re.search(r'\b(AND|OR|NOT)\b', fts_query, re.IGNORECASE):
            fts_query = " AND ".join(re.findall(r'\S+', fts_query))

        sql = f"""
            SELECT strftime('{fmt}', l.timestamp, 'unixepoch', 'localtime') AS bucket,
                   COUNT(*) AS count
            FROM logs_fts fts
            JOIN logs l ON l.id = fts.rowid
            WHERE fts.logs_fts MATCH ?
              AND l.timestamp >= ? AND l.timestamp <= ?
            GROUP BY bucket
            ORDER BY bucket
        """

        results = []
        async with self._db.execute(sql, (fts_query, time_start, time_end)) as cursor:
            rows = await cursor.fetchall()
            for r in rows:
                results.append({"bucket": r[0], "count": r[1]})

        return results

    async def get_context(
        self,
        log_id: int,
        before: int = 5,
        after: int = 5,
    ) -> dict:
        async with self._db.execute(
            "SELECT id, timestamp, source, level, content, structured_data, container_name, container_id, labels, host FROM logs WHERE id = ?",
            (log_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return {"target": None, "before": [], "after": []}

        target = self._row_to_dict(row)
        target_ts = row["timestamp"]
        target_id = row["id"]

        before_results = []
        async with self._db.execute(
            """
            SELECT id, timestamp, source, level, content, structured_data,
                   container_name, container_id, labels, host
            FROM logs
            WHERE (timestamp < ? OR (timestamp = ? AND id < ?))
            ORDER BY timestamp DESC, id DESC
            LIMIT ?
            """,
            (target_ts, target_ts, target_id, before),
        ) as cursor:
            rows = await cursor.fetchall()
            for r in rows:
                before_results.append(self._row_to_dict(r))
        before_results.reverse()

        after_results = []
        async with self._db.execute(
            """
            SELECT id, timestamp, source, level, content, structured_data,
                   container_name, container_id, labels, host
            FROM logs
            WHERE (timestamp > ? OR (timestamp = ? AND id > ?))
            ORDER BY timestamp ASC, id ASC
            LIMIT ?
            """,
            (target_ts, target_ts, target_id, after),
        ) as cursor:
            rows = await cursor.fetchall()
            for r in rows:
                after_results.append(self._row_to_dict(r))

        return {
            "target": target,
            "before": before_results,
            "after": after_results,
        }


log_storage_service = LogStorageService()
