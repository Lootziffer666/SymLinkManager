from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, TypeVar, get_args, get_origin, get_type_hints

T = TypeVar("T", bound="SerializableDataclass")


class SerializableDataclass:
    def to_dict(self) -> dict:
        return _serialize_value(asdict(self))

    @classmethod
    def from_dict(cls: type[T], data: dict) -> T:
        type_hints = get_type_hints(cls)
        kwargs = {}
        for field_name, field_type in type_hints.items():
            if field_name in data:
                kwargs[field_name] = _deserialize_value(data[field_name], field_type)
        return cls(**kwargs)


class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class RecommendedAction(str, Enum):
    KEEP = "Keep"
    PURGE = "Purge"
    RELOCATE = "Relocate"
    REVIEW = "Review"


class LinkType(str, Enum):
    JUNCTION = "Junction"
    SYMLINK = "Symlink"


class RelocationState(str, Enum):
    NOT_RELOCATED = "NotRelocated"
    RELOCATED = "Relocated"
    BROKEN_LINK = "BrokenLink"
    NEEDS_VALIDATION = "NeedsValidation"


class StorageKind(str, Enum):
    CACHE = "Cache"
    TEMP = "Temp"
    SHADER_CACHE = "ShaderCache"
    LOGS = "Logs"
    SCREENSHOTS = "Screenshots"
    CAPTURES = "Captures"
    SUPPORT_DATA = "SupportData"
    SAVE_DATA = "SaveData"
    INSTALL_DATA = "InstallData"
    UNKNOWN = "Unknown"


class ProgramSourceType(str, Enum):
    WIN32 = "Win32"
    APPX = "AppX"
    IMPORTED = "Imported"


class ProgramRecordType(str, Enum):
    APP = "App"
    MICROSOFT = "Microsoft"
    RUNTIME = "Runtime"
    DRIVER = "Driver"
    HOTFIX = "Hotfix"
    UNKNOWN = "Unknown"


class ProgramCategory(str, Enum):
    GAME = "Game"
    LAUNCHER = "Launcher"
    CREATIVE = "Creative"
    UTILITY = "Utility"
    DEVTOOL = "DevTool"
    SYSTEM_COMPONENT = "SystemComponent"
    OTHER = "Other"


class LegalStatus(str, Enum):
    FREE = "Free"
    FREE_TIER = "Free Tier"
    FREE_AVAILABLE = "Free Available"
    PAID = "Paid"
    PAID_TRIAL = "Paid/Trial"
    UNKNOWN = "Unknown"


class ActionType(str, Enum):
    PURGE = "Purge"
    RELOCATE = "Relocate"
    CREATE_LINK = "CreateLink"
    REPAIR_LINK = "RepairLink"
    REMOVE_LINK = "RemoveLink"
    UNDO = "Undo"


class ActionStatus(str, Enum):
    DRY_RUN = "DryRun"
    SUCCESS = "Success"
    PARTIAL = "Partial"
    FAILED = "Failed"


@dataclass(slots=True)
class ProgramEntry(SerializableDataclass):
    id: str
    raw_display_name: str
    normalized_name: str
    display_version: str = ""
    publisher: str = ""
    source_type: ProgramSourceType = ProgramSourceType.WIN32
    record_type: ProgramRecordType = ProgramRecordType.UNKNOWN
    category: ProgramCategory = ProgramCategory.OTHER
    risk_level: RiskLevel = RiskLevel.MEDIUM
    install_location: str = ""
    uninstall_string: str = ""
    quiet_uninstall_string: str = ""
    estimated_install_bytes: int = 0
    estimated_user_data_bytes: int = 0
    estimated_cache_bytes: int = 0
    estimated_capture_bytes: int = 0
    estimated_total_bytes: int = 0
    estimated_total_human: str = "0 B"
    estimate_confidence: str = "Low"
    estimate_notes: str = ""
    legal_status: LegalStatus = LegalStatus.UNKNOWN
    legal_alternative_hint: str = ""
    legal_alternative_candidates: list[str] = field(default_factory=list)
    duplicate_count: int = 0
    duplicate_sources: list[str] = field(default_factory=list)


@dataclass(slots=True)
class StorageItem(SerializableDataclass):
    id: str
    display_name: str
    path: str
    owner_hint: Optional[str] = None
    kind: StorageKind = StorageKind.UNKNOWN
    source: str = "KnownPath"
    risk_level: RiskLevel = RiskLevel.MEDIUM
    recommended_action: RecommendedAction = RecommendedAction.REVIEW
    reclaimable_bytes: int = 0
    movable_bytes: int = 0
    total_bytes: int = 0
    human_size: str = "0 B"
    confidence: str = "Medium"
    notes: str = ""
    linked_by_tabula: bool = False
    relocation_state: RelocationState = RelocationState.NOT_RELOCATED
    original_path: Optional[str] = None
    target_path: Optional[str] = None
    link_type: Optional[LinkType] = None


TabulaItem = StorageItem
FolderKind = StorageKind


@dataclass(slots=True)
class RelocationRecord(SerializableDataclass):
    id: str
    source_path: str
    target_path: str
    link_type: LinkType
    created_at: datetime
    owner_hint: str = ""
    validated: bool = False
    validation_notes: str = ""
    undo_supported: bool = True
    status: str = "Active"


@dataclass(slots=True)
class ActionRecord(SerializableDataclass):
    id: str
    action_type: ActionType
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: ActionStatus = ActionStatus.DRY_RUN
    source_path: str = ""
    target_path: str = ""
    bytes_affected: int = 0
    notes: str = ""


@dataclass
class ActionPlan:
    """A single planned action that can be previewed, executed, or undone."""

    action_type: str  # "delete", "uninstall", "powershell", "reg", "service", "task", "keep_merged"
    target: str  # command or path to act on
    description: str = ""
    impact_mb: float = 0.0
    risk: str = "Medium"
    requires_reboot: bool = False
    dry_run_preview: str = ""

    def model_dump(self) -> dict:
        return {
            "action_type": self.action_type,
            "target": self.target,
            "description": self.description,
            "impact_mb": self.impact_mb,
            "risk": self.risk,
            "requires_reboot": self.requires_reboot,
            "dry_run_preview": self.dry_run_preview,
        }


@dataclass
class UWPEntry:
    """An installed UWP / AppX package."""

    name: str
    package_fullname: str
    is_ai_related: bool = False
    publisher: str = ""
    install_location: str = ""
    version: str = ""


@dataclass
class TaskEntry:
    """A Windows Scheduled Task."""

    name: str
    path: str
    enabled: bool = True
    is_critical: bool = False
    last_run: str = ""
    next_run: str = ""
    status: str = "Unknown"
    description: str = ""
    run_as: str = ""
    trigger_summary: str = ""


@dataclass
class ArchiveItem:
    """A local archive or installer file."""

    path: str
    file_type: str
    size_mb: float = 0.0
    status: str = "unknown"
    overlap_installed: bool = False
    password_protected: bool = False
    notes: str = ""


@dataclass
class AutorunEntry:
    """A Windows autorun / autostart registry entry."""

    name: str
    location: str  # registry key or folder path
    entry_type: str  # "Registry", "StartupFolder"
    command: str = ""
    enabled: bool = True
    is_suspicious: bool = False
    risk: str = "Low"
    notes: str = ""


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
        if origin is list and args:
            return [_deserialize_value(item, args[0]) for item in value]
        if args:
            return _deserialize_value(value, args[0])

    if isinstance(expected_type, type) and issubclass(expected_type, Enum):
        return expected_type(value)
    if expected_type is datetime and isinstance(value, str):
        return datetime.fromisoformat(value)
    return value
