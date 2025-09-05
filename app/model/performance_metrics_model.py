from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId

class PerformanceMetricModel:
    def __init__(
        self,
        url: str,
        metrics: dict,
        device: dict,
        user_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        _id: Optional[ObjectId] = None
    ):
        self._id = _id or ObjectId()
        self._url = url
        self._metrics = metrics
        self._device = device
        self._user_id = user_id
        self._timestamp = timestamp or datetime.now(tz=timezone.utc)

    # _id solo getter
    @property
    def id(self) -> ObjectId:
        return self._id

    # url getter/setter
    @property
    def url(self) -> str:
        return self._url

    @url.setter
    def url(self, value: str):
        if not value:
            raise ValueError("URL no puede estar vacío")
        self._url = value

    # metrics getter/setter
    @property
    def metrics(self) -> dict:
        return self._metrics

    @metrics.setter
    def metrics(self, value: dict):
        # Validación básica
        required_keys = ["LCP", "INP", "CLS", "FCP"]
        for key in required_keys:
            if key not in value:
                raise ValueError(f"Metrics debe contener {key}")
        if not (0 <= value["CLS"] <= 1):
            raise ValueError("CLS debe estar entre 0 y 1")
        self._metrics = value

    # device getter/setter
    @property
    def device(self) -> dict:
        return self._device

    @device.setter
    def device(self, value: dict):
        required_keys = ["type", "os", "browser"]
        for key in required_keys:
            if key not in value:
                raise ValueError(f"Device debe contener {key}")
        self._device = value

    # user_id getter/setter
    @property
    def user_id(self) -> Optional[str]:
        return self._user_id

    @user_id.setter
    def user_id(self, value: Optional[str]):
        self._user_id = value

    # timestamp getter/setter
    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value: datetime):
        self._timestamp = value

    # Convertir a dict
    def to_dict(self) -> dict:
        return {
            "_id": self._id,
            "url": self._url,
            "metrics": self._metrics,
            "device": self._device,
            "user_id": self._user_id,
            "timestamp": self._timestamp
        }

    # Convertir a JSON serializable
    def to_json(self) -> dict:
        d = self.to_dict()
        d["_id"] = str(d["_id"])
        d["timestamp"] = d["timestamp"].isoformat()
        return d

    # Crear desde dict
    @staticmethod
    def from_dict(data: dict) -> "PerformanceMetricModel":
        return PerformanceMetricModel(
            url=data.get("url"),
            metrics=data.get("metrics"),
            device=data.get("device"),
            user_id=data.get("user_id"),
            timestamp=data.get("timestamp"),
            _id=data.get("_id")
        )
