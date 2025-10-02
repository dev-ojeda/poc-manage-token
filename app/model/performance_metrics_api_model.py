import datetime
from typing import Optional
from pydantic import BaseModel, Field

# ---------------- Thresholds ----------------
ALERT_THRESHOLDS = {
    "LCP": 2500,
    "FID": 100,
    "CLS": 0.1,
    "INP": 200,
    "TTFB": 500,
    "apiResponseTime": 1000,
}

# ---------------- Pydantic Schema ----------------
class PerformanceMetricApiModel(BaseModel):
    type: str = Field(..., max_length=50)
    category: str = Field(..., max_length=50)
    value: float
    url: Optional[str] = Field(None, max_length=255)
    method: Optional[str] = Field(None, max_length=10)
    status: Optional[str] = Field(None, max_length=20)
    role: str = Field("User", max_length=50)
    ts: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))

    def to_dict(self):
        return {
            "type": self.type,
            "category": self.category,
            "value": self.value,
            "url": self.url,
            "method": self.method,
            "status": self.status,
            "role": self.role,
            "ts": self.ts
        }