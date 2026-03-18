from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class ProgramEntry(BaseModel):
    name: str
    publisher: str = ""
    version: str = ""
    install_dir: str = ""
    uninstall_cmd: str = ""
    size_mb: float = 0.0
    confidence: str = "Low"
    category: str = "Application"
    risk: str = RiskLevel.MEDIUM.value
    is_system: bool = False
    is_duplicate: bool = False


class UWPEntry(BaseModel):
    name: str
    package_fullname: str
    is_ai_related: bool = False


class ArchiveEntry(BaseModel):
    path: str
    file_type: str
    size_mb: float
    status: str
    overlap_installed: bool = False
    password_needed: bool = False


class ScheduledTaskEntry(BaseModel):
    name: str
    path: str
    enabled: bool
    state: str = "Unknown"
    is_critical: bool = False
    orphaned: bool = False
    risk: str = RiskLevel.MEDIUM.value


class ActionPlan(BaseModel):
    action_type: str
    target: str
    description: str
    impact_mb: float = 0.0
    risk: str = RiskLevel.MEDIUM.value
    requires_reboot: bool = False
    dry_run_preview: str = ""


class DuplicateAction(ActionPlan):
    files_to_delete: list[str] = Field(default_factory=list)
    merged_file: str = ""
