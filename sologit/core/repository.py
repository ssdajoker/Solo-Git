
"""
Repository abstraction for Solo Git.

Represents a Git repository managed by Solo Git, with metadata
for tracking workpads, trunk branch, and lifecycle information.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class Repository:
    """Repository metadata and state."""
    
    id: str
    """Unique repository identifier (e.g., repo_a1b2c3d4)"""
    
    name: str
    """Human-readable repository name"""
    
    path: Path
    """Absolute path to repository on disk"""
    
    trunk_branch: str = "main"
    """Name of the trunk branch (default: main)"""
    
    created_at: datetime = field(default_factory=datetime.now)
    """When the repository was initialized"""
    
    workpad_count: int = 0
    """Number of active workpads"""
    
    source_type: Optional[str] = None
    """Source type: 'zip' or 'git'"""
    
    source_url: Optional[str] = None
    """Original Git URL if cloned from remote"""
    
    last_activity: datetime = field(default_factory=datetime.now)
    """Last activity timestamp"""
    
    def __post_init__(self) -> None:
        """Ensure path is a Path object."""
        if isinstance(self.path, str):
            self.path = Path(self.path)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "path": str(self.path),
            "trunk_branch": self.trunk_branch,
            "created_at": self.created_at.isoformat(),
            "workpad_count": self.workpad_count,
            "source_type": self.source_type,
            "source_url": self.source_url,
            "last_activity": self.last_activity.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Repository":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            path=Path(data["path"]),
            trunk_branch=data.get("trunk_branch", "main"),
            created_at=datetime.fromisoformat(data["created_at"]),
            workpad_count=data.get("workpad_count", 0),
            source_type=data.get("source_type"),
            source_url=data.get("source_url"),
            last_activity=datetime.fromisoformat(
                data.get("last_activity", data["created_at"])
            ),
        )
