
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
        # Validate inputs
        if not zip_buffer:
            raise GitEngineError("Zip buffer cannot be empty")
        if not name or not name.strip():
            raise GitEngineError("Repository name cannot be empty")
        if len(name) > 255:
            raise GitEngineError("Repository name too long (max 255 characters)")
        
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
        # Validate inputs
        if not git_url or not git_url.strip():
            raise GitEngineError("Git URL cannot be empty")
        
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
        # Validate inputs
        self._validate_repo_id(repo_id)
        if not title or not title.strip():
            raise GitEngineError("Workpad title cannot be empty")
        if len(title) > 100:
            raise GitEngineError("Workpad title too long (max 100 characters)")
        
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
        # Validate inputs
        self._validate_pad_id(pad_id)
        if not patch or not patch.strip():
            raise GitEngineError("Patch cannot be empty")
        
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
    
    def get_history(
        self, 
        repo_id: str, 
        limit: int = 50,
        branch: Optional[str] = None
    ) -> List[dict]:
        """
        Get commit history for repository.
        
        Args:
            repo_id: Repository ID
            limit: Maximum number of commits to retrieve
            branch: Branch name (default: trunk)
            
        Returns:
            List of commit dictionaries with details
        """
        repository = self.repo_db.get(repo_id)
        if not repository:
            raise RepositoryNotFoundError(f"Repository {repo_id} not found")
        
        try:
            repo = Repo(repository.path)
            branch_name = branch or repository.trunk_branch
            
            # Get commits
            commits = []
            for commit in repo.iter_commits(branch_name, max_count=limit):
                commits.append({
                    'hash': commit.hexsha,
                    'short_hash': commit.hexsha[:7],
                    'author': str(commit.author),
                    'author_email': commit.author.email,
                    'date': commit.committed_datetime.isoformat(),
                    'message': commit.message.strip(),
                    'summary': commit.summary,
                    'parents': [p.hexsha for p in commit.parents],
                })
            
            logger.debug(f"Retrieved {len(commits)} commits from {branch_name}")
            return commits
            
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            raise GitEngineError(f"Failed to get history: {e}")
    
    def get_status(self, repo_id: str, pad_id: Optional[str] = None) -> dict:
        """
        Get repository or workpad status.
        
        Args:
            repo_id: Repository ID
            pad_id: Optional workpad ID (default: trunk status)
            
        Returns:
            Status dictionary with changed files
        """
        repository = self.repo_db.get(repo_id)
        if not repository:
            raise RepositoryNotFoundError(f"Repository {repo_id} not found")
        
        try:
            repo = Repo(repository.path)
            
            # Checkout appropriate branch
            if pad_id:
                workpad = self.workpad_db.get(pad_id)
                if not workpad:
                    raise WorkpadNotFoundError(f"Workpad {pad_id} not found")
                branch = getattr(repo.heads, workpad.branch_name)
            else:
                branch = getattr(repo.heads, repository.trunk_branch)
            
            branch.checkout()
            
            # Get status
            changed_files = [item.a_path for item in repo.index.diff(None)]
            staged_files = [item.a_path for item in repo.index.diff('HEAD')]
            untracked_files = repo.untracked_files
            
            return {
                'branch': branch.name,
                'changed_files': changed_files,
                'staged_files': staged_files,
                'untracked_files': untracked_files,
                'has_changes': bool(changed_files or staged_files or untracked_files),
                'is_clean': not bool(changed_files or staged_files or untracked_files),
            }
            
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            raise GitEngineError(f"Failed to get status: {e}")
    
    def get_file_content(
        self, 
        repo_id: str, 
        file_path: str,
        ref: Optional[str] = None
    ) -> str:
        """
        Get file content at specific commit/branch.
        
        Args:
            repo_id: Repository ID
            file_path: Relative path to file
            ref: Git reference (branch, tag, commit hash), default: trunk
            
        Returns:
            File content as string
        """
        repository = self.repo_db.get(repo_id)
        if not repository:
            raise RepositoryNotFoundError(f"Repository {repo_id} not found")
        
        try:
            repo = Repo(repository.path)
            ref_name = ref or repository.trunk_branch
            
            # Get file content from git tree
            commit = repo.commit(ref_name)
            content = commit.tree[file_path].data_stream.read()
            
            # Decode if possible
            try:
                return content.decode('utf-8')
            except UnicodeDecodeError:
                # Binary file
                return f"<binary file: {len(content)} bytes>"
            
        except Exception as e:
            logger.error(f"Failed to get file content: {e}")
            raise GitEngineError(f"Failed to get file content for {file_path}: {e}")
    
    def rollback_to_checkpoint(self, pad_id: str, checkpoint_id: str) -> None:
        """
        Rollback workpad to specific checkpoint.
        
        Args:
            pad_id: Workpad ID
            checkpoint_id: Checkpoint ID (e.g., 't1', 't2')
        """
        logger.info(f"Rolling back workpad {pad_id} to checkpoint {checkpoint_id}")
        
        workpad = self.workpad_db.get(pad_id)
        if not workpad:
            raise WorkpadNotFoundError(f"Workpad {pad_id} not found")
        
        if checkpoint_id not in workpad.checkpoints:
            raise GitEngineError(
                f"Checkpoint {checkpoint_id} not found in workpad {pad_id}"
            )
        
        repository = self.repo_db[workpad.repo_id]
        
        try:
            repo = Repo(repository.path)
            
            # Ensure on workpad branch
            branch = getattr(repo.heads, workpad.branch_name)
            branch.checkout()
            
            # Get tag name
            tag_name = f"{workpad.branch_name}@{checkpoint_id}"
            
            # Reset to checkpoint
            repo.head.reset(tag_name, index=True, working_tree=True)
            
            # Update metadata - remove checkpoints after this one
            checkpoint_idx = workpad.checkpoints.index(checkpoint_id)
            workpad.checkpoints = workpad.checkpoints[:checkpoint_idx + 1]
            workpad.last_activity = datetime.now()
            self._save_metadata()
            
            logger.info(f"Rolled back to checkpoint {checkpoint_id}")
            
        except Exception as e:
            logger.error(f"Failed to rollback to checkpoint: {e}")
            raise GitEngineError(f"Failed to rollback to checkpoint: {e}")
    
    def delete_workpad(self, pad_id: str, force: bool = False) -> None:
        """
        Delete workpad without promoting.
        
        Args:
            pad_id: Workpad ID
            force: Force deletion even if has uncommitted changes
        """
        logger.info(f"Deleting workpad {pad_id}")
        
        workpad = self.workpad_db.get(pad_id)
        if not workpad:
            raise WorkpadNotFoundError(f"Workpad {pad_id} not found")
        
        repository = self.repo_db[workpad.repo_id]
        
        try:
            repo = Repo(repository.path)
            
            # Checkout trunk first
            trunk = getattr(repo.heads, repository.trunk_branch)
            trunk.checkout()
            
            # Delete branch
            repo.delete_head(workpad.branch_name, force=force)
            
            # Delete checkpoint tags
            for checkpoint_id in workpad.checkpoints:
                tag_name = f"{workpad.branch_name}@{checkpoint_id}"
                try:
                    repo.delete_tag(tag_name)
                except Exception:
                    pass  # Tag might not exist
            
            # Update metadata
            workpad.status = "deleted"
            repository.workpad_count -= 1
            repository.last_activity = datetime.now()
            self._save_metadata()
            
            logger.info(f"Workpad deleted: {pad_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete workpad: {e}")
            raise GitEngineError(f"Failed to delete workpad: {e}")
    
    def get_workpad_stats(self, pad_id: str) -> dict:
        """
        Get statistics about workpad changes.
        
        Args:
            pad_id: Workpad ID
            
        Returns:
            Statistics dictionary
        """
        workpad = self.workpad_db.get(pad_id)
        if not workpad:
            raise WorkpadNotFoundError(f"Workpad {pad_id} not found")
        
        repository = self.repo_db[workpad.repo_id]
        
        try:
            repo = Repo(repository.path)
            
            # Get diff stats
            diff_index = repo.commit(repository.trunk_branch).diff(
                repo.commit(workpad.branch_name)
            )
            
            files_changed = []
            total_insertions = 0
            total_deletions = 0
            
            for diff_item in diff_index:
                stats = {
                    'file': diff_item.a_path or diff_item.b_path,
                    'change_type': diff_item.change_type,
                }
                files_changed.append(stats)
            
            # Get commit count
            commits = list(repo.iter_commits(
                f"{repository.trunk_branch}..{workpad.branch_name}"
            ))
            
            return {
                'pad_id': pad_id,
                'title': workpad.title,
                'files_changed': len(files_changed),
                'files_details': files_changed,
                'commits_ahead': len(commits),
                'checkpoints': len(workpad.checkpoints),
                'status': workpad.status,
                'test_status': workpad.test_status,
                'created_at': workpad.created_at.isoformat(),
                'last_activity': workpad.last_activity.isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Failed to get workpad stats: {e}")
            raise GitEngineError(f"Failed to get workpad stats: {e}")
    
    def cleanup_stale_workpads(self, days: int = 7) -> List[str]:
        """
        Clean up workpads older than specified days.
        
        Args:
            days: Age threshold in days
            
        Returns:
            List of deleted workpad IDs
        """
        logger.info(f"Cleaning up workpads older than {days} days")
        
        from datetime import timedelta
        threshold = datetime.now() - timedelta(days=days)
        deleted_pads = []
        
        for pad_id, workpad in list(self.workpad_db.items()):
            if workpad.status == "active" and workpad.last_activity < threshold:
                try:
                    self.delete_workpad(pad_id, force=True)
                    deleted_pads.append(pad_id)
                    logger.info(f"Cleaned up stale workpad: {pad_id}")
                except Exception as e:
                    logger.error(f"Failed to cleanup workpad {pad_id}: {e}")
        
        logger.info(f"Cleaned up {len(deleted_pads)} stale workpads")
        return deleted_pads
    
    def list_branches(self, repo_id: str) -> List[dict]:
        """
        List all branches in repository.
        
        Args:
            repo_id: Repository ID
            
        Returns:
            List of branch information
        """
        repository = self.repo_db.get(repo_id)
        if not repository:
            raise RepositoryNotFoundError(f"Repository {repo_id} not found")
        
        try:
            repo = Repo(repository.path)
            branches = []
            
            for branch in repo.branches:
                is_trunk = branch.name == repository.trunk_branch
                is_workpad = branch.name.startswith('pads/')
                
                branches.append({
                    'name': branch.name,
                    'commit': branch.commit.hexsha,
                    'short_commit': branch.commit.hexsha[:7],
                    'is_trunk': is_trunk,
                    'is_workpad': is_workpad,
                    'last_commit_message': branch.commit.message.strip(),
                    'last_commit_date': branch.commit.committed_datetime.isoformat(),
                })
            
            return branches
            
        except Exception as e:
            logger.error(f"Failed to list branches: {e}")
            raise GitEngineError(f"Failed to list branches: {e}")
    
    def list_tags(self, repo_id: str) -> List[dict]:
        """
        List all tags in repository.
        
        Args:
            repo_id: Repository ID
            
        Returns:
            List of tag information
        """
        repository = self.repo_db.get(repo_id)
        if not repository:
            raise RepositoryNotFoundError(f"Repository {repo_id} not found")
        
        try:
            repo = Repo(repository.path)
            tags = []
            
            for tag in repo.tags:
                is_checkpoint = '@t' in tag.name
                
                tags.append({
                    'name': tag.name,
                    'commit': tag.commit.hexsha,
                    'short_commit': tag.commit.hexsha[:7],
                    'is_checkpoint': is_checkpoint,
                    'message': tag.commit.message.strip(),
                    'date': tag.commit.committed_datetime.isoformat(),
                })
            
            return tags
            
        except Exception as e:
            logger.error(f"Failed to list tags: {e}")
            raise GitEngineError(f"Failed to list tags: {e}")
    
    def create_commit(
        self, 
        repo_id: str,
        pad_id: str,
        message: str,
        files: Optional[List[str]] = None
    ) -> str:
        """
        Create a direct commit without patch.
        
        Args:
            repo_id: Repository ID
            pad_id: Workpad ID
            message: Commit message
            files: Optional list of specific files to commit (default: all)
            
        Returns:
            Commit hash
        """
        logger.info(f"Creating commit in workpad {pad_id}")
        
        workpad = self.workpad_db.get(pad_id)
        if not workpad:
            raise WorkpadNotFoundError(f"Workpad {pad_id} not found")
        
        repository = self.repo_db.get(repo_id)
        if not repository:
            raise RepositoryNotFoundError(f"Repository {repo_id} not found")
        
        try:
            repo = Repo(repository.path)
            
            # Ensure on workpad branch
            branch = getattr(repo.heads, workpad.branch_name)
            branch.checkout()
            
            # Stage files
            if files:
                repo.index.add(files)
            else:
                repo.index.add('*')
            
            # Commit
            commit = repo.index.commit(message)
            
            # Create checkpoint
            checkpoint_num = len(workpad.checkpoints) + 1
            checkpoint_id = f"t{checkpoint_num}"
            tag_name = f"{workpad.branch_name}@{checkpoint_id}"
            repo.create_tag(tag_name)
            
            # Update metadata
            workpad.checkpoints.append(checkpoint_id)
            workpad.last_activity = datetime.now()
            workpad.last_commit = commit.hexsha
            repository.last_activity = datetime.now()
            self._save_metadata()
            
            logger.info(f"Commit created: {commit.hexsha[:7]}")
            return commit.hexsha
            
        except Exception as e:
            logger.error(f"Failed to create commit: {e}")
            raise GitEngineError(f"Failed to create commit: {e}")
    
    def get_commits_ahead_behind(self, pad_id: str) -> dict:
        """
        Get number of commits ahead/behind trunk.
        
        Args:
            pad_id: Workpad ID
            
        Returns:
            Dictionary with ahead and behind counts
        """
        workpad = self.workpad_db.get(pad_id)
        if not workpad:
            raise WorkpadNotFoundError(f"Workpad {pad_id} not found")
        
        repository = self.repo_db[workpad.repo_id]
        
        try:
            repo = Repo(repository.path)
            
            trunk_commit = getattr(repo.heads, repository.trunk_branch).commit
            pad_commit = getattr(repo.heads, workpad.branch_name).commit
            
            # Commits in workpad but not in trunk (ahead)
            ahead = list(repo.iter_commits(
                f"{repository.trunk_branch}..{workpad.branch_name}"
            ))
            
            # Commits in trunk but not in workpad (behind)
            behind = list(repo.iter_commits(
                f"{workpad.branch_name}..{repository.trunk_branch}"
            ))
            
            return {
                'ahead': len(ahead),
                'behind': len(behind),
                'can_fast_forward': len(behind) == 0,
            }
            
        except Exception as e:
            logger.error(f"Failed to get commits ahead/behind: {e}")
            raise GitEngineError(f"Failed to get commits ahead/behind: {e}")
    
    def list_files(self, repo_id: str, ref: Optional[str] = None) -> List[str]:
        """
        List all tracked files in repository.
        
        Args:
            repo_id: Repository ID
            ref: Git reference (default: trunk)
            
        Returns:
            List of file paths
        """
        repository = self.repo_db.get(repo_id)
        if not repository:
            raise RepositoryNotFoundError(f"Repository {repo_id} not found")
        
        try:
            repo = Repo(repository.path)
            ref_name = ref or repository.trunk_branch
            
            commit = repo.commit(ref_name)
            files = []
            
            for item in commit.tree.traverse():
                if item.type == 'blob':  # File
                    files.append(item.path)
            
            return sorted(files)
            
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            raise GitEngineError(f"Failed to list files: {e}")
    
    def _validate_repo_id(self, repo_id: str) -> None:
        """Validate repository ID format."""
        if not repo_id or not repo_id.startswith('repo_'):
            raise GitEngineError(f"Invalid repository ID format: {repo_id}")
    
    def _validate_pad_id(self, pad_id: str) -> None:
        """Validate workpad ID format."""
        if not pad_id or not pad_id.startswith('pad_'):
            raise GitEngineError(f"Invalid workpad ID format: {pad_id}")
    
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
