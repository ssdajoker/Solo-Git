
"""
Git Engine for Solo Git.

Manages all Git operations including repository initialization,
workpad lifecycle, checkpoints, and merge operations.
"""

import json
import shutil
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4
from zipfile import ZipFile

from git import Repo, GitCommandError

from sologit.core.repository import Repository
from sologit.core.workpad import Workpad, Checkpoint
from sologit.utils.logger import get_logger

logger = get_logger(__name__)


class GitEngineError(Exception):
    """Base exception for Git Engine errors."""
    pass


class RepositoryNotFoundError(GitEngineError):
    """Repository not found."""
    pass


class WorkpadNotFoundError(GitEngineError):
    """Workpad not found."""
    pass


class CannotPromoteError(GitEngineError):
    """Workpad cannot be promoted."""
    pass


class GitEngine:
    """Core Git operations engine."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize Git Engine.
        
        Args:
            data_dir: Base directory for Solo Git data
                     (default: ~/.sologit/data)
        """
        if data_dir is None:
            data_dir = Path.home() / ".sologit" / "data"
        
        self.data_dir = Path(data_dir)
        self.repos_path = self.data_dir / "repos"
        self.metadata_path = self.data_dir / "metadata"
        
        # Create directories
        self.repos_path.mkdir(parents=True, exist_ok=True)
        self.metadata_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory databases
        self.repo_db: Dict[str, Repository] = {}
        self.workpad_db: Dict[str, Workpad] = {}
        
        # Load metadata
        self._load_metadata()
        
        logger.info(f"GitEngine initialized with data_dir={self.data_dir}")
    
    def init_from_zip(self, zip_buffer: bytes, name: str) -> str:
        """
        Initialize repository from zip file.
        
        Args:
            zip_buffer: Zip file contents as bytes
            name: Repository name
            
        Returns:
            Repository ID
        """
        logger.info(f"Initializing repository from zip: {name}")
        
        # Generate unique ID
        repo_id = f"repo_{uuid4().hex[:8]}"
        repo_path = self.repos_path / repo_id
        
        try:
            # Extract zip
            repo_path.mkdir(parents=True)
            with ZipFile(BytesIO(zip_buffer)) as zf:
                zf.extractall(repo_path)
            
            logger.debug(f"Extracted zip to {repo_path}")
            
            # Initialize Git
            repo = Repo.init(repo_path)
            repo.index.add('*')
            repo.index.commit('Initial commit from zip')
            
            # Rename default branch to main
            try:
                repo.head.reference = repo.heads.main
            except AttributeError:
                # Branch doesn't exist yet, create it
                repo.create_head('main')
                repo.head.reference = repo.heads.main
            
            logger.debug(f"Initialized Git repository at {repo_path}")
            
            # Store metadata
            repository = Repository(
                id=repo_id,
                name=name,
                path=repo_path,
                trunk_branch="main",
                created_at=datetime.now(),
                workpad_count=0,
                source_type="zip",
            )
            self.repo_db[repo_id] = repository
            self._save_metadata()
            
            logger.info(f"Repository initialized: {repo_id}")
            return repo_id
            
        except Exception as e:
            # Clean up on failure
            if repo_path.exists():
                shutil.rmtree(repo_path)
            logger.error(f"Failed to initialize repository from zip: {e}")
            raise GitEngineError(f"Failed to initialize from zip: {e}")
    
    def init_from_git(self, git_url: str, name: Optional[str] = None) -> str:
        """
        Initialize repository from Git URL.
        
        Args:
            git_url: Git repository URL
            name: Repository name (derived from URL if not provided)
            
        Returns:
            Repository ID
        """
        logger.info(f"Initializing repository from Git: {git_url}")
        
        # Generate unique ID
        repo_id = f"repo_{uuid4().hex[:8]}"
        repo_path = self.repos_path / repo_id
        
        try:
            # Clone repository
            repo_path.mkdir(parents=True)
            repo = Repo.clone_from(git_url, repo_path)
            
            logger.debug(f"Cloned repository to {repo_path}")
            
            # Detect default branch
            trunk_branch = repo.active_branch.name
            
            # Derive name from URL if not provided
            if name is None:
                name = Path(git_url).stem.replace('.git', '')
            
            # Store metadata
            repository = Repository(
                id=repo_id,
                name=name,
                path=repo_path,
                trunk_branch=trunk_branch,
                created_at=datetime.now(),
                workpad_count=0,
                source_type="git",
                source_url=git_url,
            )
            self.repo_db[repo_id] = repository
            self._save_metadata()
            
            logger.info(f"Repository initialized: {repo_id}")
            return repo_id
            
        except Exception as e:
            # Clean up on failure
            if repo_path.exists():
                shutil.rmtree(repo_path)
            logger.error(f"Failed to initialize repository from Git: {e}")
            raise GitEngineError(f"Failed to initialize from Git: {e}")
    
    def create_workpad(self, repo_id: str, title: str) -> str:
        """
        Create ephemeral workpad.
        
        Args:
            repo_id: Repository ID
            title: Human-readable workpad title
            
        Returns:
            Workpad ID
        """
        logger.info(f"Creating workpad '{title}' in repo {repo_id}")
        
        # Get repository
        repository = self.repo_db.get(repo_id)
        if not repository:
            raise RepositoryNotFoundError(f"Repository {repo_id} not found")
        
        # Generate workpad ID and branch name
        pad_id = f"pad_{uuid4().hex[:8]}"
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        title_slug = title.replace(' ', '-').lower()[:30]  # Limit length
        branch_name = f"pads/{title_slug}-{timestamp}"
        
        try:
            # Open repository
            repo = Repo(repository.path)
            
            # Ensure on trunk
            trunk = getattr(repo.heads, repository.trunk_branch)
            trunk.checkout()
            
            # Create new branch
            new_branch = repo.create_head(branch_name)
            new_branch.checkout()
            
            logger.debug(f"Created branch {branch_name}")
            
            # Store workpad metadata
            workpad = Workpad(
                id=pad_id,
                repo_id=repo_id,
                title=title,
                branch_name=branch_name,
                created_at=datetime.now(),
                checkpoints=[],
                last_activity=datetime.now(),
                status="active",
            )
            self.workpad_db[pad_id] = workpad
            repository.workpad_count += 1
            repository.last_activity = datetime.now()
            self._save_metadata()
            
            logger.info(f"Workpad created: {pad_id}")
            return pad_id
            
        except Exception as e:
            logger.error(f"Failed to create workpad: {e}")
            raise GitEngineError(f"Failed to create workpad: {e}")
    
    def apply_patch(self, pad_id: str, patch: str, message: str = "") -> str:
        """
        Apply patch to workpad and create checkpoint.
        
        Args:
            pad_id: Workpad ID
            patch: Unified diff patch
            message: Commit message
            
        Returns:
            Checkpoint ID
        """
        logger.info(f"Applying patch to workpad {pad_id}")
        
        # Get workpad
        workpad = self.workpad_db.get(pad_id)
        if not workpad:
            raise WorkpadNotFoundError(f"Workpad {pad_id} not found")
        
        repository = self.repo_db[workpad.repo_id]
        
        try:
            # Open repository
            repo = Repo(repository.path)
            
            # Ensure on correct branch
            branch = getattr(repo.heads, workpad.branch_name)
            branch.checkout()
            
            # Write patch to temporary file
            patch_file = repository.path / ".git" / "solo-git-patch.diff"
            patch_file.write_text(patch)
            
            # Apply patch
            repo.git.apply(str(patch_file), whitespace='fix')
            patch_file.unlink()  # Clean up
            
            # Stage and commit
            repo.index.add('*')
            checkpoint_num = len(workpad.checkpoints) + 1
            commit_msg = message or f"Checkpoint {checkpoint_num}"
            commit = repo.index.commit(commit_msg)
            
            # Create checkpoint
            checkpoint_id = f"t{checkpoint_num}"
            tag_name = f"{workpad.branch_name}@{checkpoint_id}"
            repo.create_tag(tag_name)
            
            # Update metadata
            workpad.checkpoints.append(checkpoint_id)
            workpad.last_activity = datetime.now()
            workpad.last_commit = commit.hexsha
            repository.last_activity = datetime.now()
            self._save_metadata()
            
            logger.info(f"Patch applied, checkpoint created: {checkpoint_id}")
            return checkpoint_id
            
        except GitCommandError as e:
            logger.error(f"Failed to apply patch: {e}")
            raise GitEngineError(f"Failed to apply patch: {e}")
    
    def can_promote(self, pad_id: str) -> bool:
        """
        Check if workpad can be promoted (fast-forward).
        
        Args:
            pad_id: Workpad ID
            
        Returns:
            True if can fast-forward merge, False otherwise
        """
        workpad = self.workpad_db.get(pad_id)
        if not workpad:
            return False
        
        repository = self.repo_db[workpad.repo_id]
        
        try:
            repo = Repo(repository.path)
            
            # Get merge base
            trunk_commit = getattr(repo.heads, repository.trunk_branch).commit
            pad_commit = getattr(repo.heads, workpad.branch_name).commit
            merge_base = repo.merge_base(trunk_commit, pad_commit)[0]
            
            # Can fast-forward if merge base == trunk HEAD
            return merge_base == trunk_commit
            
        except Exception as e:
            logger.error(f"Error checking promote eligibility: {e}")
            return False
    
    def promote_workpad(self, pad_id: str) -> str:
        """
        Promote workpad to trunk (fast-forward merge).
        
        Args:
            pad_id: Workpad ID
            
        Returns:
            Commit hash after merge
        """
        logger.info(f"Promoting workpad {pad_id}")
        
        # Get workpad
        workpad = self.workpad_db.get(pad_id)
        if not workpad:
            raise WorkpadNotFoundError(f"Workpad {pad_id} not found")
        
        repository = self.repo_db[workpad.repo_id]
        
        # Check if can promote
        if not self.can_promote(pad_id):
            raise CannotPromoteError(
                f"Cannot promote {pad_id}: not fast-forward-able. "
                "Trunk has diverged."
            )
        
        try:
            # Open repository
            repo = Repo(repository.path)
            
            # Checkout trunk
            trunk = getattr(repo.heads, repository.trunk_branch)
            trunk.checkout()
            
            # Fast-forward merge
            repo.git.merge(workpad.branch_name, ff_only=True)
            
            # Get commit hash
            commit_hash = trunk.commit.hexsha
            
            # Delete workpad branch
            repo.delete_head(workpad.branch_name, force=True)
            
            # Update metadata
            workpad.status = "promoted"
            repository.workpad_count -= 1
            repository.last_activity = datetime.now()
            self._save_metadata()
            
            logger.info(f"Workpad promoted: {pad_id} -> {commit_hash}")
            return commit_hash
            
        except GitCommandError as e:
            logger.error(f"Failed to promote workpad: {e}")
            raise GitEngineError(f"Failed to promote workpad: {e}")
    
    def revert_last_commit(self, repo_id: str) -> None:
        """
        Revert last commit on trunk (for Jenkins rollback).
        
        Args:
            repo_id: Repository ID
        """
        logger.warning(f"Reverting last commit on repo {repo_id}")
        
        repository = self.repo_db.get(repo_id)
        if not repository:
            raise RepositoryNotFoundError(f"Repository {repo_id} not found")
        
        try:
            repo = Repo(repository.path)
            trunk = getattr(repo.heads, repository.trunk_branch)
            trunk.checkout()
            
            # Hard reset to previous commit
            repo.head.reset('HEAD~1', index=True, working_tree=True)
            
            repository.last_activity = datetime.now()
            self._save_metadata()
            
            logger.info(f"Reverted last commit on {repository.trunk_branch}")
            
        except Exception as e:
            logger.error(f"Failed to revert commit: {e}")
            raise GitEngineError(f"Failed to revert commit: {e}")
    
    def get_diff(self, pad_id: str, base: str = "trunk") -> str:
        """
        Get diff between workpad and trunk.
        
        Args:
            pad_id: Workpad ID
            base: Base reference ('trunk' or commit hash)
            
        Returns:
            Unified diff string
        """
        workpad = self.workpad_db.get(pad_id)
        if not workpad:
            raise WorkpadNotFoundError(f"Workpad {pad_id} not found")
        
        repository = self.repo_db[workpad.repo_id]
        
        try:
            repo = Repo(repository.path)
            
            # Determine base reference
            base_ref = repository.trunk_branch if base == "trunk" else base
            
            # Get diff
            diff = repo.git.diff(base_ref, workpad.branch_name)
            return diff
            
        except Exception as e:
            logger.error(f"Failed to get diff: {e}")
            raise GitEngineError(f"Failed to get diff: {e}")
    
    def get_repo_map(self, repo_id: str) -> dict:
        """
        Get file tree of repository.
        
        Args:
            repo_id: Repository ID
            
        Returns:
            File tree as nested dictionary
        """
        repository = self.repo_db.get(repo_id)
        if not repository:
            raise RepositoryNotFoundError(f"Repository {repo_id} not found")
        
        # Walk directory tree
        file_tree = self._walk_directory(repository.path)
        return file_tree
    
    def get_repo(self, repo_id: str) -> Optional[Repository]:
        """Get repository by ID."""
        return self.repo_db.get(repo_id)
    
    def get_workpad(self, pad_id: str) -> Optional[Workpad]:
        """Get workpad by ID."""
        return self.workpad_db.get(pad_id)
    
    def list_repos(self) -> List[Repository]:
        """List all repositories."""
        return list(self.repo_db.values())
    
    def list_workpads(self, repo_id: Optional[str] = None) -> List[Workpad]:
        """List workpads, optionally filtered by repository."""
        workpads = list(self.workpad_db.values())
        if repo_id:
            workpads = [w for w in workpads if w.repo_id == repo_id]
        return workpads
    
    def _walk_directory(
        self, 
        path: Path, 
        max_depth: int = 5, 
        current_depth: int = 0
    ) -> Optional[dict]:
        """
        Recursively walk directory and build tree.
        
        Args:
            path: Directory path
            max_depth: Maximum recursion depth
            current_depth: Current recursion depth
            
        Returns:
            File tree dictionary or None if ignored
        """
        # Skip hidden files (except .gitignore)
        if path.name.startswith('.') and path.name not in ['.gitignore', '.env.example']:
            return None
        
        # Skip common ignore patterns
        ignore_patterns = ['node_modules', '__pycache__', '.git', 'venv', '.venv']
        if path.name in ignore_patterns:
            return None
        
        # Handle files
        if path.is_file():
            return {
                'name': path.name,
                'type': 'file',
                'size': path.stat().st_size,
                'path': str(path.relative_to(path.parent.parent))
            }
        
        # Handle directories
        if path.is_dir() and current_depth < max_depth:
            children = []
            try:
                for child in sorted(path.iterdir()):
                    child_node = self._walk_directory(child, max_depth, current_depth + 1)
                    if child_node:
                        children.append(child_node)
            except PermissionError:
                pass
            
            return {
                'name': path.name,
                'type': 'directory',
                'children': children,
                'path': str(path.relative_to(path.parent.parent))
            }
        
        return None
    
    def _load_metadata(self) -> None:
        """Load metadata from disk."""
        # Load repositories
        repos_file = self.metadata_path / "repositories.json"
        if repos_file.exists():
            try:
                data = json.loads(repos_file.read_text())
                self.repo_db = {
                    repo_id: Repository.from_dict(repo_data)
                    for repo_id, repo_data in data.items()
                }
                logger.debug(f"Loaded {len(self.repo_db)} repositories")
            except Exception as e:
                logger.error(f"Failed to load repositories: {e}")
        
        # Load workpads
        workpads_file = self.metadata_path / "workpads.json"
        if workpads_file.exists():
            try:
                data = json.loads(workpads_file.read_text())
                self.workpad_db = {
                    pad_id: Workpad.from_dict(pad_data)
                    for pad_id, pad_data in data.items()
                }
                logger.debug(f"Loaded {len(self.workpad_db)} workpads")
            except Exception as e:
                logger.error(f"Failed to load workpads: {e}")
    
    def _save_metadata(self) -> None:
        """Save metadata to disk."""
        # Save repositories
        repos_file = self.metadata_path / "repositories.json"
        repos_data = {
            repo_id: repo.to_dict()
            for repo_id, repo in self.repo_db.items()
        }
        repos_file.write_text(json.dumps(repos_data, indent=2))
        
        # Save workpads
        workpads_file = self.metadata_path / "workpads.json"
        workpads_data = {
            pad_id: workpad.to_dict()
            for pad_id, workpad in self.workpad_db.items()
        }
        workpads_file.write_text(json.dumps(workpads_data, indent=2))
        
        logger.debug("Metadata saved")
