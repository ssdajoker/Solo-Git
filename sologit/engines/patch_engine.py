
"""
Patch Engine for Solo Git.

Handles patch application, conflict detection, and validation.
"""

from pathlib import Path
from typing import Dict, List, Optional

from git import Repo, GitCommandError

from sologit.engines.git_engine import GitEngine, WorkpadNotFoundError, GitEngineError
from sologit.utils.logger import get_logger

logger = get_logger(__name__)


class PatchEngineError(Exception):
    """Base exception for Patch Engine errors."""
    pass


class PatchConflictError(PatchEngineError):
    """Patch has conflicts."""
    pass


class PatchEngine:
    """
    Patch application and validation engine.
    
    Integrates with GitEngine to apply code changes to workpads.
    """
    
    def __init__(self, git_engine: GitEngine):
        """
        Initialize Patch Engine.
        
        Args:
            git_engine: GitEngine instance
        """
        self.git_engine = git_engine
        logger.info("PatchEngine initialized")
    
    def apply_patch(
        self, 
        pad_id: str, 
        patch: str, 
        message: str = "",
        validate: bool = True
    ) -> str:
        """
        Apply patch to workpad with optional validation.
        
        Args:
            pad_id: Workpad ID
            patch: Unified diff patch
            message: Commit message
            validate: Whether to validate before applying
            
        Returns:
            Checkpoint ID
            
        Raises:
            PatchConflictError: If patch has conflicts
            PatchEngineError: If patch application fails
        """
        logger.info(f"Applying patch to workpad {pad_id} (validate={validate})")
        
        if validate:
            self.validate_patch(pad_id, patch)
        
        try:
            checkpoint_id = self.git_engine.apply_patch(pad_id, patch, message)
            logger.info(f"Patch applied successfully: {checkpoint_id}")
            return checkpoint_id
        except GitEngineError as e:
            logger.error(f"Failed to apply patch: {e}")
            raise PatchEngineError(f"Failed to apply patch: {e}")
    
    def validate_patch(self, pad_id: str, patch: str) -> bool:
        """
        Validate patch can be applied without conflicts.
        
        Args:
            pad_id: Workpad ID
            patch: Unified diff patch
            
        Returns:
            True if patch can be applied
            
        Raises:
            PatchConflictError: If patch has conflicts
        """
        logger.debug(f"Validating patch for workpad {pad_id}")
        
        # Get workpad
        workpad = self.git_engine.get_workpad(pad_id)
        if not workpad:
            raise WorkpadNotFoundError(f"Workpad {pad_id} not found")
        
        repository = self.git_engine.get_repo(workpad.repo_id)
        
        try:
            # Open repository
            repo = Repo(repository.path)
            
            # Ensure on correct branch
            branch = getattr(repo.heads, workpad.branch_name)
            branch.checkout()
            
            # Write patch to temporary file
            patch_file = repository.path / ".git" / "solo-git-validate.diff"
            patch_file.write_text(patch)
            
            # Try to apply patch (check only)
            try:
                repo.git.apply(str(patch_file), check=True, whitespace='fix')
                patch_file.unlink()  # Clean up
                logger.debug("Patch validation successful")
                return True
            except GitCommandError as e:
                patch_file.unlink()  # Clean up
                logger.warning(f"Patch validation failed: {e}")
                raise PatchConflictError(f"Patch has conflicts: {e}")
                
        except Exception as e:
            logger.error(f"Patch validation error: {e}")
            raise PatchEngineError(f"Patch validation error: {e}")
    
    def detect_conflicts(self, pad_id: str, patch: str) -> List[str]:
        """
        Detect conflicting files in patch.
        
        Args:
            pad_id: Workpad ID
            patch: Unified diff patch
            
        Returns:
            List of conflicting file paths
        """
        try:
            self.validate_patch(pad_id, patch)
            return []  # No conflicts
        except PatchConflictError:
            # Parse patch to find affected files
            affected_files = self._parse_affected_files(patch)
            return affected_files
    
    def _parse_affected_files(self, patch: str) -> List[str]:
        """
        Parse patch to extract affected file paths.
        
        Args:
            patch: Unified diff patch
            
        Returns:
            List of file paths
        """
        files = []
        for line in patch.split('\n'):
            if line.startswith('---') or line.startswith('+++'):
                # Extract file path
                parts = line.split()
                if len(parts) >= 2:
                    file_path = parts[1]
                    # Remove a/ or b/ prefix
                    if file_path.startswith(('a/', 'b/')):
                        file_path = file_path[2:]
                    if file_path and file_path != '/dev/null':
                        files.append(file_path)
        return list(set(files))
    
    def create_patch_from_files(
        self, 
        pad_id: str, 
        file_changes: Dict[str, str]
    ) -> str:
        """
        Create unified diff patch from file changes.
        
        Args:
            pad_id: Workpad ID
            file_changes: Dict mapping file paths to new content
            
        Returns:
            Unified diff patch string
        """
        logger.debug(f"Creating patch for {len(file_changes)} file(s)")
        
        workpad = self.git_engine.get_workpad(pad_id)
        if not workpad:
            raise WorkpadNotFoundError(f"Workpad {pad_id} not found")
        
        repository = self.git_engine.get_repo(workpad.repo_id)
        
        try:
            repo = Repo(repository.path)
            branch = getattr(repo.heads, workpad.branch_name)
            branch.checkout()
            
            # Apply file changes
            for file_path, content in file_changes.items():
                full_path = repository.path / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)
            
            # Generate diff
            diff = repo.git.diff('HEAD', '--', *file_changes.keys())
            return diff
            
        except Exception as e:
            logger.error(f"Failed to create patch: {e}")
            raise PatchEngineError(f"Failed to create patch: {e}")
