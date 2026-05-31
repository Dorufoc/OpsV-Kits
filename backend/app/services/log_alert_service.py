from __future__ import annotations

import re
import time
from typing import Optional

import aiosqlite

from app.services.log_storage_service import log_storage_service


class LogAlertService:
    def __init__(self):
        self._counters: dict[int, list[float]] = {}
        self._last_alert_time: dict[int, float] = {}
        self._notification_callbacks: list = []
        self._rules_cache: list[dict] = []

    async def _get_db(self) -> aiosqlite.Connection:
        if log_storage_service._db is None:
            await log_storage_service.initialize()
        return log_storage_service._db

    async def create_rule(self, rule: dict) -> int:
        db = await self._get_db()
        cursor = await db.execute(
            """
            INSERT INTO alert_rules (name, pattern, pattern_type, time_window, threshold, enabled, silence_period, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rule["name"],
                rule["pattern"],
                rule.get("pattern_type", "keyword"),
                rule.get("time_window", 300),
                rule.get("threshold", 1),
                1 if rule.get("enabled", True) else 0,
                rule.get("silence_period", 3600),
                time.time(),
            ),
        )
        await db.commit()
        rule_id = cursor.lastrowid
        await self._refresh_cache()
        return rule_id

    async def update_rule(self, rule_id: int, updates: dict) -> None:
        db = await self._get_db()
        allowed = {"name", "pattern", "pattern_type", "time_window", "threshold", "enabled", "silence_period"}
        sets = []
        params = []
        for key, value in updates.items():
            if key in allowed:
                if key == "enabled":
                    sets.append(f"{key} = ?")
                    params.append(1 if value else 0)
                else:
                    sets.append(f"{key} = ?")
                    params.append(value)
        if not sets:
            return
        params.append(rule_id)
        await db.execute(
            f"UPDATE alert_rules SET {', '.join(sets)} WHERE id = ?",
            params,
        )
        await db.commit()
        await self._refresh_cache()

    async def delete_rule(self, rule_id: int) -> None:
        db = await self._get_db()
        await db.execute("DELETE FROM alert_events WHERE rule_id = ?", (rule_id,))
        await db.execute("DELETE FROM alert_rules WHERE id = ?", (rule_id,))
        await db.commit()
        self._counters.pop(rule_id, None)
        self._last_alert_time.pop(rule_id, None)
        await self._refresh_cache()

    async def get_rule(self, rule_id: int) -> dict | None:
        db = await self._get_db()
        async with db.execute("SELECT * FROM alert_rules WHERE id = ?", (rule_id,)) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return self._rule_row_to_dict(row)

    async def get_rules(self, enabled_only: bool = False) -> list[dict]:
        db = await self._get_db()
        if enabled_only:
            sql = "SELECT * FROM alert_rules WHERE enabled = 1"
            params = ()
        else:
            sql = "SELECT * FROM alert_rules"
            params = ()
        results = []
        async with db.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                results.append(self._rule_row_to_dict(row))
        return results

    async def toggle_rule(self, rule_id: int, enabled: bool) -> None:
        db = await self._get_db()
        await db.execute(
            "UPDATE alert_rules SET enabled = ? WHERE id = ?",
            (1 if enabled else 0, rule_id),
        )
        await db.commit()
        if not enabled:
            self._counters.pop(rule_id, None)
        await self._refresh_cache()

    def match_keyword(self, content: str, pattern: str) -> bool:
        return pattern.lower() in content.lower()

    def match_regex(self, content: str, pattern: str) -> bool:
        try:
            return bool(re.search(pattern, content))
        except re.error:
            return False

    def match_level(self, level: str, pattern: str) -> bool:
        return level.upper() == pattern.upper()

    def match(self, log_entry: dict, rule: dict) -> bool:
        pattern_type = rule.get("pattern_type", "keyword")
        pattern = rule.get("pattern", "")
        if pattern_type == "keyword":
            return self.match_keyword(log_entry.get("content", ""), pattern)
        elif pattern_type == "regex":
            return self.match_regex(log_entry.get("content", ""), pattern)
        elif pattern_type == "level":
            return self.match_level(log_entry.get("level", ""), pattern)
        return False

    async def check_alert(self, log_entry: dict) -> list[dict]:
        alerts = []
        now = time.time()
        for rule in self._rules_cache:
            if not rule.get("enabled", False):
                continue
            if not self.match(log_entry, rule):
                continue
            rule_id = rule["id"]
            if rule_id not in self._counters:
                self._counters[rule_id] = []
            self._counters[rule_id].append(now)
            time_window = rule.get("time_window", 300)
            cutoff = now - time_window
            self._counters[rule_id] = [ts for ts in self._counters[rule_id] if ts > cutoff]
            match_count = len(self._counters[rule_id])
            threshold = rule.get("threshold", 1)
            if match_count >= threshold:
                silence_period = rule.get("silence_period", 3600)
                last_time = self._last_alert_time.get(rule_id, 0)
                in_silence = (now - last_time) < silence_period
                notified = not in_silence
                if notified:
                    self._last_alert_time[rule_id] = now
                self._counters[rule_id] = [ts for ts in self._counters[rule_id] if ts > now - time_window]
                detail = f"Rule '{rule['name']}' triggered: {match_count} matches in {time_window}s window"
                await self.record_event(rule_id, match_count, notified, detail)
                alert_info = {
                    "rule_id": rule_id,
                    "rule_name": rule["name"],
                    "pattern": rule["pattern"],
                    "match_count": match_count,
                    "triggered_at": now,
                    "detail": detail,
                }
                if notified:
                    for callback in self._notification_callbacks:
                        try:
                            callback(alert_info)
                        except Exception:
                            pass
                alerts.append(alert_info)
        return alerts

    async def record_event(self, rule_id: int, match_count: int, notified: bool, detail: str = "") -> int:
        db = await self._get_db()
        cursor = await db.execute(
            """
            INSERT INTO alert_events (rule_id, triggered_at, match_count, notified, detail)
            VALUES (?, ?, ?, ?, ?)
            """,
            (rule_id, time.time(), match_count, 1 if notified else 0, detail),
        )
        await db.commit()
        return cursor.lastrowid

    async def get_events(self, rule_id: int = None, limit: int = 50) -> list[dict]:
        db = await self._get_db()
        if rule_id is not None:
            sql = "SELECT * FROM alert_events WHERE rule_id = ? ORDER BY triggered_at DESC LIMIT ?"
            params = (rule_id, limit)
        else:
            sql = "SELECT * FROM alert_events ORDER BY triggered_at DESC LIMIT ?"
            params = (limit,)
        results = []
        async with db.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                results.append(self._event_row_to_dict(row))
        return results

    async def get_recent_events(self, hours: int = 24, limit: int = 100) -> list[dict]:
        db = await self._get_db()
        cutoff = time.time() - hours * 3600
        sql = "SELECT * FROM alert_events WHERE triggered_at >= ? ORDER BY triggered_at DESC LIMIT ?"
        results = []
        async with db.execute(sql, (cutoff, limit)) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                results.append(self._event_row_to_dict(row))
        return results

    def register_notification(self, callback) -> None:
        if callback not in self._notification_callbacks:
            self._notification_callbacks.append(callback)

    def unregister_notification(self, callback) -> None:
        if callback in self._notification_callbacks:
            self._notification_callbacks.remove(callback)

    async def initialize(self) -> None:
        await self._refresh_cache()

    async def shutdown(self) -> None:
        self._counters.clear()
        self._last_alert_time.clear()
        self._rules_cache.clear()

    async def _refresh_cache(self) -> None:
        self._rules_cache = await self.get_rules(enabled_only=True)

    def _rule_row_to_dict(self, row: aiosqlite.Row) -> dict:
        return {
            "id": row["id"],
            "name": row["name"],
            "pattern": row["pattern"],
            "pattern_type": row["pattern_type"],
            "time_window": row["time_window"],
            "threshold": row["threshold"],
            "enabled": bool(row["enabled"]),
            "silence_period": row["silence_period"],
            "created_at": row["created_at"],
        }

    def _event_row_to_dict(self, row: aiosqlite.Row) -> dict:
        return {
            "id": row["id"],
            "rule_id": row["rule_id"],
            "triggered_at": row["triggered_at"],
            "match_count": row["match_count"],
            "notified": bool(row["notified"]),
            "detail": row["detail"],
        }


log_alert_service = LogAlertService()
