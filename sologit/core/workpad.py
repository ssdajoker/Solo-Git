
"""
Workpad abstraction for Solo Git.

Workpads are ephemeral, disposable workspaces that replace traditional
branches. They are automatically named, tracked, and cleaned up.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Workpad:
    """Workpad metadata and state."""
    
    id: str
    """Unique workpad identifier (e.g., pad_x9y8z7w6)"""
    
    repo_id: str
    """Repository this workpad belongs to"""
    
    title: str
    """Human-readable workpad title"""
    
    branch_name: str
    """Git branch name (e.g., pads/add-login-20251016-1423)"""
    
    created_at: datetime = field(default_factory=datetime.now)
    """When the workpad was created"""
    
    checkpoints: List[str] = field(default_factory=list)
    """List of checkpoint IDs (e.g., ['t1', 't2', 't3'])"""
    
    last_activity: datetime = field(default_factory=datetime.now)
    """Last activity timestamp"""
    
    status: str = "active"
    """Workpad status: active, promoted, deleted"""
    
    test_status: Optional[str] = None
    """Last test result: green, red, or None"""
    
    last_commit: Optional[str] = None
    """Last commit hash in workpad"""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "repo_id": self.repo_id,
            "title": self.title,
            "branch_name": self.branch_name,
            "created_at": self.created_at.isoformat(),
            "checkpoints": self.checkpoints,
            "last_activity": self.last_activity.isoformat(),
            "status": self.status,
            "test_status": self.test_status,
            "last_commit": self.last_commit,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Workpad":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            repo_id=data["repo_id"],
            title=data["title"],
            branch_name=data["branch_name"],
            created_at=datetime.fromisoformat(data["created_at"]),
            checkpoints=data.get("checkpoints", []),
            last_activity=datetime.fromisoformat(
                data.get("last_activity", data["created_at"])
            ),
            status=data.get("status", "active"),
            test_status=data.get("test_status"),
            last_commit=data.get("last_commit"),
        )


@dataclass
class Checkpoint:
    """Checkpoint (autosave) metadata."""
    
    id: str
    """Checkpoint identifier (e.g., t1, t2, t3)"""
    
    pad_id: str
    """Workpad this checkpoint belongs to"""
    
    tag_name: str
    """Git tag name (e.g., pads/add-login-20251016-1423@t1)"""
    
    commit_hash: str
    """Git commit hash"""
    
    message: str = ""
    """Optional checkpoint message"""
    
    created_at: datetime = field(default_factory=datetime.now)
    """When the checkpoint was created"""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "pad_id": self.pad_id,
            "tag_name": self.tag_name,
            "commit_hash": self.commit_hash,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Checkpoint":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            pad_id=data["pad_id"],
            tag_name=data["tag_name"],
            commit_hash=data["commit_hash"],
            message=data.get("message", ""),
            created_at=datetime.fromisoformat(data["created_at"]),
        )
