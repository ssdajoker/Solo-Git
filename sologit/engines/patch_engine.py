
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


class PatchValidationError(PatchEngineError):
    """Patch validation failed."""
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
                
        except PatchConflictError:
            # Re-raise PatchConflictError without wrapping
            raise
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
        
        try:
            workpad = self.git_engine.get_workpad(pad_id)
            if not workpad:
                raise WorkpadNotFoundError(f"Workpad {pad_id} not found")

            repository = self.git_engine.get_repo(workpad.repo_id)

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
            
        except WorkpadNotFoundError:
            raise
        except GitEngineError as e:
            logger.error(f"Git engine error during patch creation: {e}")
            raise PatchEngineError(f"Failed to create patch: {e}") from e
        except Exception as e:
            logger.error(f"Failed to create patch: {e}")
            raise PatchEngineError(f"Failed to create patch: {e}") from e
    
    def get_patch_stats(self, patch: str) -> dict:
        """
        Get statistics about a patch.
        
        Args:
            patch: Unified diff patch
            
        Returns:
            Dictionary with patch statistics
        """
        lines = patch.split('\n')
        
        files_affected = set()
        additions = 0
        deletions = 0
        hunks = 0
        
        for line in lines:
            # Count hunks
            if line.startswith('@@'):
                hunks += 1
            # Count additions
            elif line.startswith('+') and not line.startswith('+++'):
                additions += 1
            # Count deletions
            elif line.startswith('-') and not line.startswith('---'):
                deletions += 1
            # Track files
            elif line.startswith('---') or line.startswith('+++'):
                parts = line.split()
                if len(parts) >= 2:
                    file_path = parts[1]
                    if file_path.startswith(('a/', 'b/')):
                        file_path = file_path[2:]
                    if file_path and file_path != '/dev/null':
                        files_affected.add(file_path)
        
        total_changes = additions + deletions
        
        return {
            'files_affected': len(files_affected),
            'files_list': sorted(list(files_affected)),
            'additions': additions,
            'deletions': deletions,
            'total_changes': total_changes,
            'hunks': hunks,
            'complexity': self._calculate_patch_complexity(
                total_changes, len(files_affected), hunks
            ),
        }
    
    def _calculate_patch_complexity(
        self, 
        total_changes: int, 
        files_affected: int, 
        hunks: int
    ) -> str:
        """
        Calculate patch complexity level.
        
        Args:
            total_changes: Total lines changed
            files_affected: Number of files affected
            hunks: Number of hunks
            
        Returns:
            Complexity level (trivial, simple, moderate, complex, very_complex)
        """
        if total_changes < 10 and files_affected == 1:
            return "trivial"
        elif total_changes < 50 and files_affected <= 3:
            return "simple"
        elif total_changes < 200 and files_affected <= 10:
            return "moderate"
        elif total_changes < 500 and files_affected <= 20:
            return "complex"
        else:
            return "very_complex"
    
    def preview_patch(self, pad_id: str, patch: str) -> dict:
        """
        Preview patch application without applying it.
        
        Args:
            pad_id: Workpad ID
            patch: Unified diff patch
            
        Returns:
            Preview dictionary with analysis
        """
        logger.info(f"Previewing patch for workpad {pad_id}")
        
        # Get patch stats
        stats = self.get_patch_stats(patch)
        
        # Check for conflicts
        has_conflicts = False
        conflict_files = []
        try:
            self.validate_patch(pad_id, patch)
        except PatchConflictError:
            has_conflicts = True
            conflict_files = self.detect_conflicts(pad_id, patch)
        
        # Get workpad info
        workpad = self.git_engine.get_workpad(pad_id)
        
        return {
            'pad_id': pad_id,
            'pad_title': workpad.title if workpad else "Unknown",
            'can_apply': not has_conflicts,
            'has_conflicts': has_conflicts,
            'conflict_files': conflict_files,
            'stats': stats,
            'recommendation': self._get_application_recommendation(
                stats, has_conflicts
            ),
        }
    
    def _get_application_recommendation(
        self, 
        stats: dict, 
        has_conflicts: bool
    ) -> str:
        """
        Get recommendation for patch application.
        
        Args:
            stats: Patch statistics
            has_conflicts: Whether patch has conflicts
            
        Returns:
            Recommendation string
        """
        if has_conflicts:
            return "MANUAL_RESOLUTION_REQUIRED - Patch has conflicts"
        
        complexity = stats.get('complexity', 'unknown')
        
        if complexity in ['trivial', 'simple']:
            return "SAFE_TO_APPLY - Low complexity, low risk"
        elif complexity == 'moderate':
            return "REVIEW_RECOMMENDED - Moderate complexity"
        else:
            return "CAREFUL_REVIEW_REQUIRED - High complexity, higher risk"
    
    def detect_conflicts_detailed(self, pad_id: str, patch: str) -> dict:
        """
        Detailed conflict detection with analysis.
        
        Args:
            pad_id: Workpad ID
            patch: Unified diff patch
            
        Returns:
            Detailed conflict information
        """
        try:
            self.validate_patch(pad_id, patch)
            return {
                'has_conflicts': False,
                'conflicting_files': [],
                'conflict_details': [],
                'can_apply': True,
            }
        except PatchConflictError as e:
            conflicting_files = self.detect_conflicts(pad_id, patch)
            
            return {
                'has_conflicts': True,
                'conflicting_files': conflicting_files,
                'conflict_details': [
                    {
                        'file': f,
                        'reason': 'File modified in workpad or patch does not apply cleanly',
                    }
                    for f in conflicting_files
                ],
                'can_apply': False,
                'error_message': str(e),
            }
    
    def split_patch_by_file(self, patch: str) -> Dict[str, str]:
        """
        Split a multi-file patch into individual patches per file.
        
        Args:
            patch: Unified diff patch
            
        Returns:
            Dictionary mapping file paths to their individual patches
        """
        patches = {}
        current_file = None
        current_patch_lines = []
        
        for line in patch.split('\n'):
            if line.startswith('diff --git'):
                # Save previous patch
                if current_file and current_patch_lines:
                    patches[current_file] = '\n'.join(current_patch_lines)
                
                # Start new patch
                current_patch_lines = [line]
                # Extract filename from diff header
                parts = line.split()
                if len(parts) >= 4:
                    file_path = parts[2]
                    if file_path.startswith('a/'):
                        file_path = file_path[2:]
                    current_file = file_path
            else:
                current_patch_lines.append(line)
        
        # Save last patch
        if current_file and current_patch_lines:
            patches[current_file] = '\n'.join(current_patch_lines)
        
        return patches
    
    def combine_patches(self, patches: List[str]) -> str:
        """
        Combine multiple patches into a single patch.
        
        Args:
            patches: List of unified diff patches
            
        Returns:
            Combined patch
        """
        if not patches:
            return ""
        
        # Simply concatenate patches
        combined = '\n\n'.join(p.strip() for p in patches if p.strip())
        return combined
    
    def validate_patch_syntax(self, patch: str) -> dict:
        """
        Validate patch syntax without applying to repository.
        
        Args:
            patch: Unified diff patch
            
        Returns:
            Validation result dictionary
        """
        errors = []
        warnings = []
        
        if not patch or not patch.strip():
            errors.append("Patch is empty")
            return {
                'valid': False,
                'errors': errors,
                'warnings': warnings,
            }
        
        lines = patch.split('\n')
        has_diff_header = False
        has_hunks = False
        
        for line in lines:
            if line.startswith('diff --git'):
                has_diff_header = True
            elif line.startswith('@@'):
                has_hunks = True
        
        if not has_diff_header:
            warnings.append("No 'diff --git' header found")
        
        if not has_hunks:
            warnings.append("No hunks found in patch")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
        }
    
    def apply_patch_interactive(
        self, 
        pad_id: str, 
        patch: str, 
        message: str = "",
        dry_run: bool = False
    ) -> dict:
        """
        Apply patch with preview and validation.
        
        Args:
            pad_id: Workpad ID
            patch: Unified diff patch
            message: Commit message
            dry_run: If True, only validate without applying
            
        Returns:
            Application result dictionary
        """
        # Validate syntax
        syntax_check = self.validate_patch_syntax(patch)
        if not syntax_check['valid']:
            return {
                'applied': False,
                'reason': 'invalid_syntax',
                'errors': syntax_check['errors'],
            }
        
        # Preview patch
        preview = self.preview_patch(pad_id, patch)
        
        if not preview['can_apply']:
            return {
                'applied': False,
                'reason': 'has_conflicts',
                'preview': preview,
            }
        
        if dry_run:
            return {
                'applied': False,
                'reason': 'dry_run',
                'preview': preview,
                'would_succeed': True,
            }
        
        # Apply patch
        try:
            checkpoint_id = self.apply_patch(pad_id, patch, message, validate=True)
            return {
                'applied': True,
                'checkpoint_id': checkpoint_id,
                'preview': preview,
            }
        except Exception as e:
            return {
                'applied': False,
                'reason': 'application_failed',
                'error': str(e),
                'preview': preview,
            }
