from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, TypeVar, get_args, get_origin, get_type_hints

T = TypeVar("T", bound="SerializableDataclass")


class SerializableDataclass:
    def to_dict(self) -> dict:
        data = asdict(self)
        return _serialize_value(data)

    @classmethod
    def from_dict(cls: type[T], data: dict) -> T:
        type_hints = get_type_hints(cls)
        kwargs = {}
        for field_name, field_type in type_hints.items():
            if field_name not in data:
                continue
            kwargs[field_name] = _deserialize_value(data[field_name], field_type)
        return cls(**kwargs)


class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class PurgeKind(str, Enum):
    TEMP = "Temp"
    CACHE = "Cache"
    SHADER_CACHE = "ShaderCache"
    LOGS = "Logs"
    THUMBNAILS = "Thumbnails"
    SCREENSHOTS = "Screenshots"
    CAPTURES = "Captures"
    INSTALLER_LEFTOVERS = "InstallerLeftovers"
    UPDATER_RESIDUE = "UpdaterResidue"
    APP_RESIDUE = "AppResidue"
    ORPHANED_APP_DATA = "OrphanedAppData"
    UNKNOWN = "Unknown"


class RecommendedAction(str, Enum):
    PURGE = "Purge"
    REVIEW = "Review"
    KEEP = "Keep"


class ExecutionMode(str, Enum):
    DRY_RUN = "DryRun"
    SAFE = "RecycleBinPreferred"
    AGGRESSIVE = "PermanentDelete"


@dataclass(slots=True)
class PurgeItem(SerializableDataclass):
    id: str
    selected: bool = False
    display_name: str = ""
    path: str = ""
    owner_hint: Optional[str] = None
    kind: PurgeKind = PurgeKind.UNKNOWN
    risk_level: RiskLevel = RiskLevel.MEDIUM
    recommended_action: RecommendedAction = RecommendedAction.REVIEW
    size_bytes: int = 0
    size_human: str = "0 B"
    confidence: str = "Medium"
    detection_source: str = "KnownPath"
    notes: Optional[str] = None
    review_required: bool = False


@dataclass(slots=True)
class PurgeRun(SerializableDataclass):
    id: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    mode: ExecutionMode = ExecutionMode.DRY_RUN
    selected_item_count: int = 0
    estimated_bytes: int = 0
    deleted_bytes: Optional[int] = None
    skipped_count: int = 0
    failed_count: int = 0
    log_path: str = ""


def _serialize_value(value):
    if isinstance(value, dict):
        return {key: _serialize_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _deserialize_value(value, expected_type):
    origin = get_origin(expected_type)
    if origin is not None:
        args = [arg for arg in get_args(expected_type) if arg is not type(None)]
        if args:
            return _deserialize_value(value, args[0])

    if isinstance(expected_type, type) and issubclass(expected_type, Enum):
        return expected_type(value)
    if expected_type is datetime and isinstance(value, str):
        return datetime.fromisoformat(value)
    return value
