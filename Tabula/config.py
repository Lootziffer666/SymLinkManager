# Configuration for Tabula

import os
from pathlib import Path

# System Paths — resolved dynamically so they work on any Windows user account
system_paths = {
    "documents": str(Path(os.path.expandvars(r"%USERPROFILE%\Documents"))),
    "downloads": str(Path(os.path.expandvars(r"%USERPROFILE%\Downloads"))),
    "desktop": str(Path(os.path.expandvars(r"%USERPROFILE%\Desktop"))),
}

# Risk Categories
risk_categories = ['Low', 'Medium', 'High', 'Critical']

# Risk Levels
risk_levels = {
    'Low': 'Minor impact',
    'Medium': 'Significant impact',
    'High': 'Severe impact',
    'Critical': 'Catastrophic impact'
}

# Thresholds
thresholds = {
    'low': 10,
    'medium': 20,
    'high': 30,
    'critical': 50
}

# Storage Location Patterns
storage_location_patterns = {
    "local": str(Path(os.path.expandvars(r"%USERPROFILE%\Storage\Local"))),
    "backup": str(Path(os.path.expandvars(r"%USERPROFILE%\Storage\Backup"))),
}