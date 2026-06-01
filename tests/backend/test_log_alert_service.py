import os
import tempfile
from unittest.mock import MagicMock

import pytest
import pytest_asyncio

from app.services.log_storage_service import log_storage_service
from app.services.log_alert_service import LogAlertService


@pytest_asyncio.fixture
async def alert_svc():
    if log_storage_service._db is not None:
        await log_storage_service.shutdown()
    alert = LogAlertService()
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_alert_svc.db")
        await log_storage_service.initialize(db_path=db_path)
        await alert.initialize()
        yield alert
        await alert.shutdown()
        await log_storage_service.shutdown()


class TestGetDbWhenNone:
    @pytest.mark.asyncio
    async def test_get_db_initializes_when_none(self):
        if log_storage_service._db is not None:
            await log_storage_service.shutdown()
        alert = LogAlertService()
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_getdb.db")
            await log_storage_service.initialize(db_path=db_path)
            db = await alert._get_db()
            assert db is not None
            await alert.shutdown()
            await log_storage_service.shutdown()


class TestUpdateRuleEnabledField:
    @pytest.mark.asyncio
    async def test_update_rule_enabled_false(self, alert_svc):
        rule_id = await alert_svc.create_rule({
            "name": "Enabled Test",
            "pattern": "error",
            "pattern_type": "keyword",
            "enabled": True,
        })
        await alert_svc.update_rule(rule_id, {"enabled": False})
        rule = await alert_svc.get_rule(rule_id)
        assert rule["enabled"] is False

    @pytest.mark.asyncio
    async def test_update_rule_enabled_true(self, alert_svc):
        rule_id = await alert_svc.create_rule({
            "name": "Disabled Test",
            "pattern": "error",
            "pattern_type": "keyword",
            "enabled": False,
        })
        await alert_svc.update_rule(rule_id, {"enabled": True})
        rule = await alert_svc.get_rule(rule_id)
        assert rule["enabled"] is True


class TestUpdateRuleNoValidFields:
    @pytest.mark.asyncio
    async def test_update_rule_no_allowed_keys(self, alert_svc):
        rule_id = await alert_svc.create_rule({
            "name": "No Update",
            "pattern": "error",
            "pattern_type": "keyword",
        })
        await alert_svc.update_rule(rule_id, {"invalid_key": "value"})
        rule = await alert_svc.get_rule(rule_id)
        assert rule["name"] == "No Update"


class TestMatchRegexInvalid:
    def test_match_regex_invalid_pattern(self, alert_svc):
        result = alert_svc.match_regex("some content", "[invalid(regex")
        assert result is False


class TestMatchMethodRegexAndLevel:
    def test_match_regex_type(self, alert_svc):
        rule = {"pattern_type": "regex", "pattern": r"Error \d+"}
        assert alert_svc.match({"content": "Error 500"}, rule) is True
        assert alert_svc.match({"content": "Warning"}, rule) is False

    def test_match_level_type(self, alert_svc):
        rule = {"pattern_type": "level", "pattern": "ERROR"}
        assert alert_svc.match({"level": "ERROR", "content": ""}, rule) is True
        assert alert_svc.match({"level": "INFO", "content": ""}, rule) is False

    def test_match_unknown_type(self, alert_svc):
        rule = {"pattern_type": "unknown", "pattern": "test"}
        assert alert_svc.match({"content": "test"}, rule) is False


class TestCheckAlertDisabledAndNonMatching:
    @pytest.mark.asyncio
    async def test_check_alert_disabled_rule(self, alert_svc):
        rule_id = await alert_svc.create_rule({
            "name": "Disabled Rule",
            "pattern": "error",
            "pattern_type": "keyword",
            "enabled": False,
        })
        log_entry = {"content": "error in system", "level": "ERROR"}
        alerts = await alert_svc.check_alert(log_entry)
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_check_alert_non_matching(self, alert_svc):
        await alert_svc.create_rule({
            "name": "No Match",
            "pattern": "critical",
            "pattern_type": "keyword",
            "enabled": True,
        })
        log_entry = {"content": "just info", "level": "INFO"}
        alerts = await alert_svc.check_alert(log_entry)
        assert len(alerts) == 0


class TestNotificationCallbackException:
    @pytest.mark.asyncio
    async def test_callback_exception_suppressed(self, alert_svc):
        rule_id = await alert_svc.create_rule({
            "name": "Callback Test",
            "pattern": "error",
            "pattern_type": "keyword",
            "threshold": 1,
            "silence_period": 0,
        })

        bad_callback = MagicMock(side_effect=Exception("callback error"))
        alert_svc.register_notification(bad_callback)

        log_entry = {"content": "error occurred", "level": "ERROR"}
        alerts = await alert_svc.check_alert(log_entry)
        assert len(alerts) >= 1


class TestGetEventsWithoutRuleId:
    @pytest.mark.asyncio
    async def test_get_events_all_rules(self, alert_svc):
        rule_id = await alert_svc.create_rule({
            "name": "Event Test",
            "pattern": "error",
            "pattern_type": "keyword",
            "threshold": 1,
            "silence_period": 0,
        })
        log_entry = {"content": "error occurred", "level": "ERROR"}
        await alert_svc.check_alert(log_entry)

        events = await alert_svc.get_events()
        assert len(events) >= 1


class TestGetRecentEvents:
    @pytest.mark.asyncio
    async def test_get_recent_events(self, alert_svc):
        rule_id = await alert_svc.create_rule({
            "name": "Recent Test",
            "pattern": "error",
            "pattern_type": "keyword",
            "threshold": 1,
            "silence_period": 0,
        })
        log_entry = {"content": "error occurred", "level": "ERROR"}
        await alert_svc.check_alert(log_entry)

        events = await alert_svc.get_recent_events(hours=24)
        assert len(events) >= 1


class TestUnregisterNotification:
    def test_unregister_notification(self, alert_svc):
        callback = MagicMock()
        alert_svc.register_notification(callback)
        assert callback in alert_svc._notification_callbacks
        alert_svc.unregister_notification(callback)
        assert callback not in alert_svc._notification_callbacks

    def test_unregister_nonexistent_callback(self, alert_svc):
        callback = MagicMock()
        alert_svc.unregister_notification(callback)
