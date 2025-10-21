"""
Command History and Undo/Redo System for Heaven Interface.

Provides command history tracking, persistence, and undo/redo capabilities.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum

from sologit.utils.logger import get_logger

logger = get_logger(__name__)


CLI_HISTORY_PATH = Path.home() / ".sologit" / "history.txt"
CLI_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)


class CommandType(Enum):
    """Types of commands that can be undone."""
    WORKPAD_CREATE = "workpad_create"
    WORKPAD_DELETE = "workpad_delete"
    WORKPAD_PROMOTE = "workpad_promote"
    FILE_EDIT = "file_edit"
    COMMIT = "commit"
    REVERT = "revert"
    PATCH_APPLY = "patch_apply"
    CONFIG_CHANGE = "config_change"
    CLI_COMMAND = "cli_command"


@dataclass
class CommandEntry:
    """A single command history entry."""
    id: str
    type: CommandType
    timestamp: datetime
    description: str
    arguments: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    undoable: bool = True
    undo_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'type': self.type.value,
            'timestamp': self.timestamp.isoformat(),
            'description': self.description,
            'arguments': self.arguments,
            'result': self.result,
            'undoable': self.undoable,
            'undo_data': self.undo_data
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CommandEntry':
        """Create from dictionary."""
        return cls(
            id=data['id'],
            type=CommandType(data['type']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            description=data['description'],
            arguments=data['arguments'],
            result=data.get('result'),
            undoable=data.get('undoable', True),
            undo_data=data.get('undo_data')
        )


class CommandHistory:
    """
    Command history manager with undo/redo support.
    
    Maintains a stack of executed commands and provides
    undo/redo capabilities with state tracking.
    """
    
    def __init__(self, history_file: Optional[Path] = None, max_size: int = 1000):
        """
        Initialize command history.
        
        Args:
            history_file: Path to history file (default: ~/.sologit/history.json)
            max_size: Maximum number of entries to keep in memory
        """
        if history_file is None:
            history_file = Path.home() / ".sologit" / "history.json"

        self.history_file = Path(history_file)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.cli_history_file = CLI_HISTORY_PATH
        self.cli_history_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.cli_history_file.exists():
            self.cli_history_file.touch()
        
        self.max_size = max_size
        self.entries: List[CommandEntry] = []
        self.current_index = -1  # Points to the current command
        
        # Undo handlers: command_type -> (undo_func, redo_func)
        self.undo_handlers: Dict[CommandType, tuple] = {}
        
        # Load history from file
        self.load()
        
        logger.info(f"CommandHistory initialized with {len(self.entries)} entries")
    
    def add_command(
        self,
        command_type: CommandType,
        description: str,
        arguments: Dict[str, Any],
        result: Optional[Dict[str, Any]] = None,
        undoable: bool = True,
        undo_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a command to history.
        
        Args:
            command_type: Type of command
            description: Human-readable description
            arguments: Command arguments
            result: Command result
            undoable: Whether this command can be undone
            undo_data: Data needed to undo the command
            
        Returns:
            Command ID
        """
        # Generate unique ID
        command_id = f"cmd_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Create entry
        entry = CommandEntry(
            id=command_id,
            type=command_type,
            timestamp=datetime.now(),
            description=description,
            arguments=arguments,
            result=result,
            undoable=undoable,
            undo_data=undo_data
        )
        
        # If we're not at the end of history, discard forward entries
        if self.current_index < len(self.entries) - 1:
            self.entries = self.entries[:self.current_index + 1]
        
        # Add to history
        self.entries.append(entry)
        self.current_index = len(self.entries) - 1
        
        # Enforce max size
        if len(self.entries) > self.max_size:
            self.entries = self.entries[-self.max_size:]
            self.current_index = len(self.entries) - 1
        
        # Save to disk
        self.save()
        
        logger.debug(f"Added command to history: {description}")

        return command_id

    def record_cli_command(
        self,
        command: str,
        arguments: Optional[Dict[str, Any]] = None,
        record_text: bool = True
    ) -> str:
        """Record a CLI command execution in history."""
        command_id = self.add_command(
            command_type=CommandType.CLI_COMMAND,
            description=command,
            arguments=arguments or {},
            result=None,
            undoable=False,
        )

        if record_text:
            self._append_cli_history(command)

        return command_id
    
    def can_undo(self) -> bool:
        """Check if undo is available."""
        if self.current_index < 0:
            return False
        
        entry = self.entries[self.current_index]
        return entry.undoable and entry.type in self.undo_handlers
    
    def can_redo(self) -> bool:
        """Check if redo is available."""
        if self.current_index >= len(self.entries) - 1:
            return False
        
        next_entry = self.entries[self.current_index + 1]
        return next_entry.undoable and next_entry.type in self.undo_handlers
    
    def undo(self) -> Optional[CommandEntry]:
        """
        Undo the last command.
        
        Returns:
            The undone command entry, or None if undo not available
        """
        if not self.can_undo():
            logger.warning("Cannot undo: no undoable commands")
            return None
        
        entry = self.entries[self.current_index]
        
        try:
            # Get undo handler
            undo_func, _ = self.undo_handlers[entry.type]
            
            # Execute undo
            logger.info(f"Undoing command: {entry.description}")
            undo_func(entry)
            
            # Move index back
            self.current_index -= 1
            
            return entry
            
        except Exception as e:
            logger.error(f"Undo failed: {e}", exc_info=True)
            raise
    
    def redo(self) -> Optional[CommandEntry]:
        """
        Redo the next command.
        
        Returns:
            The redone command entry, or None if redo not available
        """
        if not self.can_redo():
            logger.warning("Cannot redo: no commands to redo")
            return None
        
        # Move to next entry
        self.current_index += 1
        entry = self.entries[self.current_index]
        
        try:
            # Get redo handler
            _, redo_func = self.undo_handlers[entry.type]
            
            # Execute redo
            logger.info(f"Redoing command: {entry.description}")
            redo_func(entry)
            
            return entry
            
        except Exception as e:
            logger.error(f"Redo failed: {e}", exc_info=True)
            # Revert index
            self.current_index -= 1
            raise

    def update_command_result(self, command_id: str, result: Dict[str, Any]) -> None:
        """Update stored result for a command."""
        entry = self.get_entry(command_id)
        if not entry:
            return

        entry.result = result
        self.save()
    
    def register_undo_handler(
        self,
        command_type: CommandType,
        undo_func: Callable[[CommandEntry], None],
        redo_func: Callable[[CommandEntry], None]
    ) -> None:
        """
        Register undo/redo handlers for a command type.
        
        Args:
            command_type: Command type to register
            undo_func: Function to undo command
            redo_func: Function to redo command
        """
        self.undo_handlers[command_type] = (undo_func, redo_func)
        logger.debug(f"Registered undo handler for {command_type.value}")
    
    def get_history(self, limit: Optional[int] = None) -> List[CommandEntry]:
        """
        Get command history.
        
        Args:
            limit: Maximum number of entries to return (most recent first)
            
        Returns:
            List of command entries
        """
        entries = list(reversed(self.entries))
        if limit:
            entries = entries[:limit]
        return entries
    
    def get_entry(self, command_id: str) -> Optional[CommandEntry]:
        """Get a command entry by ID."""
        for entry in self.entries:
            if entry.id == command_id:
                return entry
        return None
    
    def clear(self) -> None:
        """Clear all history."""
        self.entries.clear()
        self.current_index = -1
        self.save()
        logger.info("Command history cleared")
    
    def save(self) -> None:
        """Save history to disk."""
        try:
            data = {
                'entries': [entry.to_dict() for entry in self.entries],
                'current_index': self.current_index
            }

            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved command history to {self.history_file}")

        except Exception as e:
            logger.error(f"Failed to save history: {e}", exc_info=True)
    
    def load(self) -> None:
        """Load history from disk."""
        if not self.history_file.exists():
            logger.debug("No history file found, starting fresh")
            return
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.entries = [
                CommandEntry.from_dict(entry_data)
                for entry_data in data.get('entries', [])
            ]
            self.current_index = data.get('current_index', -1)
            
            logger.info(f"Loaded {len(self.entries)} commands from history")
            
        except Exception as e:
            logger.error(f"Failed to load history: {e}", exc_info=True)
            self.entries = []
            self.current_index = -1
    
    def search(self, query: str) -> List[CommandEntry]:
        """
        Search command history.
        
        Args:
            query: Search query (matches description or arguments)
            
        Returns:
            List of matching entries
        """
        query_lower = query.lower()
        matches = []
        
        for entry in reversed(self.entries):
            # Search in description
            if query_lower in entry.description.lower():
                matches.append(entry)
                continue
            
            # Search in arguments
            args_str = json.dumps(entry.arguments).lower()
            if query_lower in args_str:
                matches.append(entry)
        
        return matches
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get history statistics."""
        if not self.entries:
            return {
                'total_commands': 0,
                'undoable_commands': 0,
                'by_type': {}
            }
        
        by_type = {}
        undoable_count = 0
        
        for entry in self.entries:
            # Count by type
            type_name = entry.type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1
            
            # Count undoable
            if entry.undoable:
                undoable_count += 1
        
        return {
            'total_commands': len(self.entries),
            'undoable_commands': undoable_count,
            'by_type': by_type,
            'current_index': self.current_index,
            'can_undo': self.can_undo(),
            'can_redo': self.can_redo()
        }

    def get_recent_cli_history(self, limit: Optional[int] = None) -> List[str]:
        """Return plain CLI history strings from the CLI history file."""
        lines = self._load_cli_history()
        if limit is None or limit >= len(lines):
            return lines
        return lines[-limit:]

    def _append_cli_history(self, command: str) -> None:
        """Append a CLI command string to the persistent CLI history file."""
        if not command:
            return

        try:
            with self.cli_history_file.open('a', encoding='utf-8') as f:
                f.write(command + "\n")
        except Exception as e:
            logger.error(f"Failed to append CLI history: {e}", exc_info=True)

    def _load_cli_history(self) -> List[str]:
        """Load CLI history strings from disk."""
        if not self.cli_history_file.exists():
            return []

        try:
            with self.cli_history_file.open('r', encoding='utf-8') as f:
                return [line.rstrip('\n') for line in f if line.strip()]
        except Exception as e:
            logger.error(f"Failed to load CLI history: {e}", exc_info=True)
            return []


# Global command history instance
_command_history: Optional[CommandHistory] = None


def get_command_history() -> CommandHistory:
    """Get the global command history instance."""
    global _command_history
    if _command_history is None:
        _command_history = CommandHistory()
    return _command_history


def reset_command_history() -> None:
    """Reset the global command history (useful for testing)."""
    global _command_history
    _command_history = None


# Convenience functions


def append_cli_history(command: str) -> None:
    """Append a command string directly to the CLI history file."""
    history = get_command_history()
    history._append_cli_history(command)


def get_cli_history_path() -> Path:
    """Return the path used for storing CLI history strings."""
    return CLI_HISTORY_PATH

def add_command(
    command_type: CommandType,
    description: str,
    arguments: Dict[str, Any],
    **kwargs
) -> str:
    """Add a command to global history."""
    return get_command_history().add_command(
        command_type, description, arguments, **kwargs
    )


def undo() -> Optional[CommandEntry]:
    """Undo the last command."""
    return get_command_history().undo()


def redo() -> Optional[CommandEntry]:
    """Redo the next command."""
    return get_command_history().redo()


def can_undo() -> bool:
    """Check if undo is available."""
    return get_command_history().can_undo()


def can_redo() -> bool:
    """Check if redo is available."""
    return get_command_history().can_redo()


def register_undo_handler(
    command_type: CommandType,
    undo_func: Callable[[CommandEntry], None],
    redo_func: Callable[[CommandEntry], None]
) -> None:
    """Register undo/redo handler."""
    get_command_history().register_undo_handler(command_type, undo_func, redo_func)
