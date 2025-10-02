import datetime
from datetime import timezone
from typing import Literal, Optional
from pydantic import BaseModel, Field
class AlertModel(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    metric: str = Field(..., description="Tipo de métrica: LCP, CLS, apiResponseTime...")
    severity: Literal["warning", "critical"] = Field(..., description="Nivel de alerta")
    value: float = Field(..., description="Valor registrado de la métrica")
    threshold: float = Field(..., description="Umbral configurado para esa métrica")
    page: Optional[str] = Field(None, description="Ruta o URL donde ocurrió la alerta")
    ts: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(timezone.utc))

    def to_dict(self, normalize_ts: bool = False):
        data = {
            "metric": self.metric,
            "severity": self.severity,
            "value": self.value,
            "threshold": self.threshold,
            "page": self.page,
            "ts": self.ts
        }
        if normalize_ts and isinstance(self.ts, datetime.datetime):
            data["ts"] = self.ts.isoformat()
        return data