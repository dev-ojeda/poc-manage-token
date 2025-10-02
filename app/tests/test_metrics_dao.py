import datetime
import pytest
import numpy as np
from unittest.mock import MagicMock, patch

from app.dao.metrics_dao import MetricsDAO
from app.model.metrics_model import MetricModel


@pytest.fixture
def dao():
    """DAO con mocks para DB y Alerts"""
    dao = MetricsDAO()
    dao.db = MagicMock()
    dao.dao_class_alert = MagicMock()
    dao.thresholds = {"default": {"apiResponseTime": 1000}}
    dao.percentiles_config = {"apiResponseTime": [0.5, 0.9]}
    return dao


def test_create_metrics_inserts_document(dao):
    metric = MagicMock()
    metric.to_dict.return_value = {"name": "apiResponseTime", "value": 1200}
    dao.create_metrics(metric)
    dao.db.insert_with_log.assert_called_once()


def test_find_with_sort_and_limit(dao):
    cursor_mock = MagicMock()
    cursor_mock.sort.return_value = cursor_mock
    cursor_mock.limit.return_value = [{"foo": "bar"}]
    dao.db.find.return_value = cursor_mock

    result = dao.find(query={"name": "apiResponseTime"}, sort=[("timestamp", -1)], limit=5)
    assert isinstance(result, list)
    cursor_mock.sort.assert_called_once()
    cursor_mock.limit.assert_called_once_with(5)


def test_summarize_metric_triggers_alert(dao):
    values = [1000, 1500, 2000]
    page = "/home"
    name = "apiResponseTime"
    threshold = 1000

    dao.add_alert = MagicMock()  # espiar
    result = dao.summarize_metric(page, name, values, threshold)

    assert "avg" in result
    assert "p50" in result and "p90" in result
    dao.add_alert.assert_called()  # debería lanzar alerta porque 2000 > threshold


def test_add_alert_creates_alert_model(dao):
    now = datetime.datetime.now(datetime.timezone.utc)
    page = "/home"
    name = "apiResponseTime"
    value = 3000
    threshold = 1000

    with patch("app.dao.metrics_dao.AlertModel") as AlertModelMock:
        alert_instance = MagicMock()
        AlertModelMock.return_value = alert_instance

        dao.add_alert(page, name, value, threshold, "p90", 3)

        dao.dao_class_alert.create.assert_called_once_with(alert=alert_instance, context="Crear Alert")


def test_aggregate_timeline_builds_pipeline(dao):
    # Mock resultado de aggregate
    fake_result = [{
        "_id": {"bucket": datetime.datetime(2025, 9, 20, 12, 0), "url": "/api/profile", "method": "GET"},
        "avg": 100, "min": 50, "max": 200, "count": 3
    }]
    dao.db.aggregate.return_value = fake_result

    result = dao.aggregate_timeline(category="endpoint", interval="minute", limit=1)

    assert len(result) == 1
    assert result[0]["url"] == "/api/profile"
    assert result[0]["method"] == "GET"
    assert result[0]["count"] == 3


def test_find_alerts_since(dao):
    cutoff = datetime.datetime(2025, 9, 20, tzinfo=datetime.timezone.utc)
    dao.find_alerts_since(cutoff)
    dao.db.find.assert_called()

