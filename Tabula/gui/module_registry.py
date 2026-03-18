from __future__ import annotations

from gui.modules.archive_module import ArchiveModule
from gui.modules.duplicates_module import DuplicatesModule
from gui.modules.micro_apps_module import MicroAppsModule
from gui.modules.module_manager_module import ModuleManagerModule
from gui.modules.plan_execute_module import PlanExecuteModule
from gui.modules.privacy_module import PrivacyModule
from gui.modules.programs_module import ProgramsModule
from gui.modules.tasks_services_module import TasksServicesModule
from gui.modules.uwp_ai_module import UwpAiModule

MODULES = [
    ModuleManagerModule,
    ProgramsModule,
    ArchiveModule,
    UwpAiModule,
    TasksServicesModule,
    PrivacyModule,
    DuplicatesModule,
    MicroAppsModule,
    PlanExecuteModule,
]
