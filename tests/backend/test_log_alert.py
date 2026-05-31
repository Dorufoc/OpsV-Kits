import os
import tempfile

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
        db_path = os.path.join(tmpdir, "test_alert.db")
        await log_storage_service.initialize(db_path=db_path)
        await alert.initialize()
        yield alert
        await alert.shutdown()
        await log_storage_service.shutdown()


@pytest.mark.asyncio
async def test_create_rule(alert_svc):
    rule_id = await alert_svc.create_rule({
        "name": "Test Rule",
        "pattern": "error",
        "pattern_type": "keyword",
        "time_window": 300,
        "threshold": 1,
        "enabled": True,
        "silence_period": 3600,
    })
    assert rule_id > 0


@pytest.mark.asyncio
async def test_get_rules(alert_svc):
    await alert_svc.create_rule({
        "name": "Rule 1",
        "pattern": "error",
        "pattern_type": "keyword",
        "time_window": 300,
        "threshold": 1,
        "enabled": True,
        "silence_period": 3600,
    })
    rules = await alert_svc.get_rules()
    assert len(rules) >= 1
    assert rules[0]["name"] == "Rule 1"


@pytest.mark.asyncio
async def test_update_rule(alert_svc):
    rule_id = await alert_svc.create_rule({
        "name": "Original",
        "pattern": "error",
        "pattern_type": "keyword",
        "time_window": 300,
        "threshold": 1,
        "enabled": True,
        "silence_period": 3600,
    })
    await alert_svc.update_rule(rule_id, {"name": "Updated", "threshold": 5})
    rule = await alert_svc.get_rule(rule_id)
    assert rule["name"] == "Updated"
    assert rule["threshold"] == 5


@pytest.mark.asyncio
async def test_delete_rule(alert_svc):
    rule_id = await alert_svc.create_rule({
        "name": "To Delete",
        "pattern": "error",
        "pattern_type": "keyword",
        "time_window": 300,
        "threshold": 1,
        "enabled": True,
        "silence_period": 3600,
    })
    await alert_svc.delete_rule(rule_id)
    rule = await alert_svc.get_rule(rule_id)
    assert rule is None


@pytest.mark.asyncio
async def test_toggle_rule(alert_svc):
    rule_id = await alert_svc.create_rule({
        "name": "Toggle Test",
        "pattern": "error",
        "pattern_type": "keyword",
        "time_window": 300,
        "threshold": 1,
        "enabled": True,
        "silence_period": 3600,
    })
    await alert_svc.toggle_rule(rule_id, False)
    rule = await alert_svc.get_rule(rule_id)
    assert rule["enabled"] is False


@pytest.mark.asyncio
async def test_match_keyword(alert_svc):
    assert alert_svc.match_keyword("An error occurred", "error") is True
    assert alert_svc.match_keyword("All good", "error") is False


@pytest.mark.asyncio
async def test_match_regex(alert_svc):
    assert alert_svc.match_regex("Error code 500", r"Error code \d+") is True
    assert alert_svc.match_regex("All good", r"Error code \d+") is False


@pytest.mark.asyncio
async def test_match_level(alert_svc):
    assert alert_svc.match_level("ERROR", "ERROR") is True
    assert alert_svc.match_level("INFO", "ERROR") is False


@pytest.mark.asyncio
async def test_check_alert_triggers(alert_svc):
    rule_id = await alert_svc.create_rule({
        "name": "Trigger Test",
        "pattern": "error",
        "pattern_type": "keyword",
        "time_window": 300,
        "threshold": 1,
        "enabled": True,
        "silence_period": 3600,
    })

    notifications = []
    alert_svc.register_notification(lambda alert: notifications.append(alert))

    log_entry = {"content": "error in system", "level": "ERROR", "source": "test"}
    triggered = await alert_svc.check_alert(log_entry)
    assert len(triggered) >= 1
    assert triggered[0]["rule_id"] == rule_id


@pytest.mark.asyncio
async def test_get_events(alert_svc):
    rule_id = await alert_svc.create_rule({
        "name": "Event Test",
        "pattern": "error",
        "pattern_type": "keyword",
        "time_window": 300,
        "threshold": 1,
        "enabled": True,
        "silence_period": 3600,
    })

    log_entry = {"content": "error in system", "level": "ERROR", "source": "test"}
    await alert_svc.check_alert(log_entry)

    events = await alert_svc.get_events(rule_id=rule_id)
    assert len(events) >= 1
