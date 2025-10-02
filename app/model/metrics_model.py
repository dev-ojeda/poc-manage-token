import datetime
from datetime import timezone
from typing import Optional

class MetricModel:
    _alert_cache = {}

    def __init__(
        self,
        name: str,
        value: float,
        category: str,
        role: str = "User",
        page: Optional[str] = None,
        url: Optional[str] = None,
        os: Optional[str] = None,
        browser: Optional[str] = None,
        metric_id: Optional[str] = None,
        timestamp: Optional[datetime.datetime] = None,
    ):
        self.name = name
        self.value = float(value)
        self.category = category
        self.role = role
        self.page = page
        self.url = url
        self.os = os
        self.browser = browser
        self.metric_id = metric_id
        self.timestamp = (
            timestamp
            if isinstance(timestamp, datetime.datetime)
            else datetime.datetime.fromtimestamp(
                timestamp / 1000, tz=timezone.utc
            ) if timestamp else datetime.datetime.now(tz=timezone.utc)
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "category": self.category,
            "role": self.role,
            "value": self.value,
            "page": self.page,
            "url": self.url,
            "os": self.os,
            "browser": self.browser,
            "metric_id": self.metric_id,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MetricModel":
        return cls(
            name=data.get("type"),
            value=data.get("value", 0),
            category=data.get("category"),   # 👈 aquí fijo category según el origen
            url=data.get("url"),
            page=data.get("page"),
            role=data.get("role", "User"),
            os=data.get("os"),
            browser=data.get("browser"),
            metric_id=data.get("metric_id"),
            timestamp=data.get("timestamp"),
        )

    @classmethod
    def from_documents(cls, documents: list[dict]) -> list["MetricModel"]:
        return [cls.from_dict(doc) for doc in documents]