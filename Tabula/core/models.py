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


class FolderKind(str, Enum):
    CACHE = "Cache"
    TEMP = "Temp"
    SHADER_CACHE = "ShaderCache"
    LOGS = "Logs"
    SCREENSHOTS = "Screenshots"
    SUPPORT_DATA = "SupportData"
    SAVE_DATA = "SaveData"
    INSTALL_DATA = "InstallData"
    UNKNOWN = "Unknown"


class RecommendedAction(str, Enum):
    KEEP = "Keep"
    PURGE = "Purge"
    RELOCATE = "Relocate"
    REVIEW = "Review"


class RelocationState(str, Enum):
    NOT_RELOCATED = "NotRelocated"
    RELOCATED = "Relocated"
    BROKEN_LINK = "BrokenLink"
    NEEDS_VALIDATION = "NeedsValidation"


class LinkType(str, Enum):
    JUNCTION = "Junction"
    SYMLINK = "Symlink"

class LinkType(str, Enum):
    JUNCTION = "Junction"
    SYMLINK = "Symlink"

@dataclass(slots=True)
class TabulaItem(SerializableDataclass):
    id: str
    display_name: str
    path: str
    normalized_path: str
    source_type: str = "KnownPath"
    owner_hint: Optional[str] = None
    kind: FolderKind = FolderKind.UNKNOWN
    risk_level: RiskLevel = RiskLevel.MEDIUM
    recommended_action: RecommendedAction = RecommendedAction.REVIEW
    size_bytes: int = 0
    size_human: str = "0 B"
    item_count: Optional[int] = None
    confidence: str = "Medium"
    notes: Optional[str] = None
    managed_by_tabula: bool = False
    relocation_state: RelocationState = RelocationState.NOT_RELOCATED
    original_path: Optional[str] = None
    target_path: Optional[str] = None
    link_type: Optional[LinkType] = None
    last_validated_at: Optional[datetime] = None


@dataclass(slots=True)
class RelocationRecord(SerializableDataclass):
    id: str
    source_path: str
    target_path: str
    link_type: LinkType
    created_at: datetime
    validated: bool = False
    validation_notes: Optional[str] = None
    undo_supported: bool = True
    status: str = "Active"


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
