"""
Git State Synchronizer.

Bridges the StateManager with GitEngine to ensure state stays synchronized
with actual git operations. This provides a unified interface that combines
JSON state tracking with real git operations.
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

from sologit.state.manager import StateManager
from sologit.state.schema import CommitNode
from sologit.engines.git_engine import GitEngine, GitEngineError
from sologit.utils.logger import get_logger

logger = get_logger(__name__)


class GitStateSync:
    """
    Synchronizes state between StateManager (JSON) and GitEngine (actual git).
    
    This is the primary interface for CLI operations - it ensures that
    every git operation is tracked in the state system and vice versa.
    """
    
    def __init__(self, state_dir: Optional[Path] = None, data_dir: Optional[Path] = None):
        """
        Initialize Git State Sync.
        
        Args:
            state_dir: StateManager data directory
            data_dir: GitEngine data directory
        """
        self.state_manager = StateManager(state_dir=state_dir)
        self.git_engine = GitEngine(data_dir=data_dir)
        logger.info("GitStateSync initialized")
    
    # Repository Operations
    
    def init_repo_from_zip(self, zip_buffer: bytes, name: str) -> Dict[str, Any]:
        """
        Initialize repository from zip and sync state.
        
        Args:
            zip_buffer: Zip file contents
            name: Repository name
            
        Returns:
            Dictionary with repo_id and metadata
        """
        logger.info(f"Initializing repo from zip: {name}")
        
        # Create in git
        repo_id = self.git_engine.init_from_zip(zip_buffer, name)
        repo = self.git_engine.get_repo(repo_id)
        
        # Sync to state manager
        self.state_manager.create_repository(
            repo_id=repo.id,
            name=repo.name,
            path=str(repo.path)
        )
        
        # Set as active
        self.state_manager.set_active_context(repo_id=repo_id)
        
        # Sync initial commit
        self._sync_commits(repo_id)
        
        logger.info(f"Repository {repo_id} initialized and synced")
        
        return {
            'repo_id': repo.id,
            'name': repo.name,
            'path': str(repo.path),
            'trunk_branch': repo.trunk_branch
        }
    
    def init_repo_from_git(self, git_url: str, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Initialize repository from git URL and sync state.
        
        Args:
            git_url: Git repository URL
            name: Repository name (derived from URL if None)
            
        Returns:
            Dictionary with repo_id and metadata
        """
        logger.info(f"Initializing repo from git: {git_url}")
        
        # Create in git
        repo_id = self.git_engine.init_from_git(git_url, name)
        repo = self.git_engine.get_repo(repo_id)
        
        # Sync to state manager
        self.state_manager.create_repository(
            repo_id=repo.id,
            name=repo.name,
            path=str(repo.path)
        )
        
        # Set as active
        self.state_manager.set_active_context(repo_id=repo_id)
        
        # Sync commits
        self._sync_commits(repo_id)
        
        logger.info(f"Repository {repo_id} initialized and synced")

        return {
            'repo_id': repo.id,
            'name': repo.name,
            'path': str(repo.path),
            'trunk_branch': repo.trunk_branch,
            'source_url': git_url
        }

    def create_empty_repo(self, name: str, path: Optional[str] = None) -> Dict[str, Any]:
        """Create an empty repository and synchronize state."""

        logger.info(f"Creating empty repository: {name}")

        repo_id = self.git_engine.create_empty_repo(name, Path(path) if path else None)
        repo = self.git_engine.get_repo(repo_id)

        self.state_manager.create_repository(
            repo_id=repo.id,
            name=repo.name,
            path=str(repo.path)
        )

        self.state_manager.set_active_context(repo_id=repo_id)
        self._sync_commits(repo_id)

        return {
            'repo_id': repo.id,
            'name': repo.name,
            'path': str(repo.path),
            'trunk_branch': repo.trunk_branch,
            'source_type': repo.source_type,
        }
    def get_repo(self, repo_id: str) -> Optional[Dict[str, Any]]:
        """Get repository info from both state and git."""
        repo = self.git_engine.get_repo(repo_id)
        if not repo:
            return None
        
        repo_state = self.state_manager.get_repository(repo_id)
        
        return {
            'id': repo.id,
            'name': repo.name,
            'path': str(repo.path),
            'trunk_branch': repo.trunk_branch,
            'created_at': repo.created_at.isoformat(),
            'workpad_count': repo.workpad_count,
            'source_type': repo.source_type,
            'source_url': repo.source_url,
            'state': repo_state.to_dict() if repo_state else None
        }
    
    def list_repos(self) -> List[Dict[str, Any]]:
        """List all repositories."""
        repos = self.git_engine.list_repos()
        return [self.get_repo(repo.id) for repo in repos]
    
    # Workpad Operations
    
    def create_workpad(self, repo_id: str, title: str) -> Dict[str, Any]:
        """
        Create workpad in git and sync state.
        
        Args:
            repo_id: Repository ID
            title: Workpad title
            
        Returns:
            Dictionary with workpad info
        """
        logger.info(f"Creating workpad: {title} in {repo_id}")
        
        # Create in git
        pad_id = self.git_engine.create_workpad(repo_id, title)
        workpad = self.git_engine.get_workpad(pad_id)
        
        # Sync to state manager
        self.state_manager.create_workpad(
            workpad_id=workpad.id,
            repo_id=workpad.repo_id,
            title=workpad.title,
            branch_name=workpad.branch_name,
            base_commit=workpad.last_commit or "HEAD"
        )
        
        # Set as active
        self.state_manager.set_active_context(workpad_id=pad_id)
        
        logger.info(f"Workpad {pad_id} created and synced")
        
        return {
            'workpad_id': workpad.id,
            'repo_id': workpad.repo_id,
            'title': workpad.title,
            'branch_name': workpad.branch_name,
            'status': workpad.status
        }
    
    def get_workpad(self, pad_id: str) -> Optional[Dict[str, Any]]:
        """Get workpad info from both state and git."""
        workpad = self.git_engine.get_workpad(pad_id)
        if not workpad:
            return None

        workpad_state = self.state_manager.get_workpad(pad_id)

        return {
            'id': workpad.id,
            'repo_id': workpad.repo_id,
            'title': workpad.title,
            'branch_name': workpad.branch_name,
            'created_at': workpad.created_at.isoformat(),
            'status': workpad.status,
            'test_status': workpad.test_status,
            'last_commit': workpad.last_commit,
            'checkpoints': workpad.checkpoints,
            'state': workpad_state.to_dict() if workpad_state else None
        }

    def get_workpad_diff_summary(self, pad_id: str, base: str = "trunk") -> Dict[str, Any]:
        """Get diff summary for a workpad relative to a base branch."""

        return self.git_engine.get_workpad_diff_summary(pad_id, base=base)
    
    def list_workpads(self, repo_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List workpads for a repository."""
        workpads = self.git_engine.list_workpads(repo_id)
        return [self.get_workpad(pad.id) for pad in workpads]
    
    def apply_patch(self, pad_id: str, patch: str, message: str = "Apply patch") -> str:
        """
        Apply patch to workpad and sync state.
        
        Args:
            pad_id: Workpad ID
            patch: Patch content
            message: Commit message
            
        Returns:
            Commit hash
        """
        logger.info(f"Applying patch to {pad_id}")
        
        # Apply in git
        commit_hash = self.git_engine.apply_patch(pad_id, patch, message)
        
        # Update workpad state
        self.state_manager.update_workpad(
            pad_id,
            last_commit=commit_hash,
            updated_at=datetime.utcnow().isoformat()
        )
        
        # Sync commits
        workpad = self.git_engine.get_workpad(pad_id)
        if workpad:
            self._sync_commits(workpad.repo_id)
        
        logger.info(f"Patch applied: {commit_hash}")
        return commit_hash
    
    def promote_workpad(self, pad_id: str) -> str:
        """
        Promote workpad to trunk and sync state.
        
        Args:
            pad_id: Workpad ID
            
        Returns:
            Merge commit hash
        """
        logger.info(f"Promoting workpad {pad_id}")
        
        # Check if can promote
        if not self.git_engine.can_promote(pad_id):
            raise GitEngineError(f"Workpad {pad_id} cannot be promoted (tests must be green)")
        
        # Promote in git
        merge_commit = self.git_engine.promote_workpad(pad_id)
        
        # Update workpad state
        self.state_manager.update_workpad(
            pad_id,
            status="promoted",
            updated_at=datetime.utcnow().isoformat()
        )
        
        # Sync commits
        workpad = self.git_engine.get_workpad(pad_id)
        if workpad:
            self._sync_commits(workpad.repo_id)
        
        logger.info(f"Workpad promoted: {merge_commit}")
        return merge_commit
    
    def delete_workpad(self, pad_id: str, force: bool = False) -> None:
        """
        Delete workpad and update state.
        
        Args:
            pad_id: Workpad ID
            force: Force delete even if not merged
        """
        logger.info(f"Deleting workpad {pad_id}")
        
        # Delete in git
        self.git_engine.delete_workpad(pad_id, force)
        
        # Update state
        self.state_manager.update_workpad(
            pad_id,
            status="deleted",
            updated_at=datetime.utcnow().isoformat()
        )

        logger.info(f"Workpad {pad_id} deleted")

    def delete_repository(self, repo_id: str, remove_files: bool = True) -> None:
        """Delete repository and remove associated state."""

        logger.info(f"Deleting repository {repo_id}")

        repo = self.git_engine.get_repo(repo_id)
        if not repo:
            raise GitEngineError(f"Repository {repo_id} not found")

        self.git_engine.delete_repository(repo_id, remove_files=remove_files)
        self.state_manager.delete_repository(repo_id)

        context = self.state_manager.get_active_context()
        if context.get('repo_id') == repo_id or (
            context.get('workpad_id') and
            not self.state_manager.get_workpad(context['workpad_id'])
        ):
            self.state_manager.set_active_context(repo_id=None, workpad_id=None)

    # Test Operations
    
    def create_test_run(self, workpad_id: Optional[str], target: str = "fast") -> Dict[str, Any]:
        """
        Create test run and track in state.
        
        Args:
            workpad_id: Workpad ID (None for trunk tests)
            target: Test target (fast/full)
            
        Returns:
            Test run info
        """
        test_run = self.state_manager.create_test_run(workpad_id, target)
        
        return {
            'run_id': test_run.run_id,
            'workpad_id': test_run.workpad_id,
            'target': test_run.target,
            'status': test_run.status,
            'started_at': test_run.started_at
        }
    
    def update_test_run(self, run_id: str, status: str, 
                       output: Optional[str] = None,
                       exit_code: Optional[int] = None) -> None:
        """
        Update test run state.
        
        Args:
            run_id: Test run ID
            status: New status (running/passed/failed)
            output: Test output
            exit_code: Exit code
        """
        updates = {'status': status}
        
        if output is not None:
            updates['output'] = output
        
        if exit_code is not None:
            updates['exit_code'] = exit_code
        
        if status in ['passed', 'failed']:
            updates['completed_at'] = datetime.utcnow().isoformat()
        
        self.state_manager.update_test_run(run_id, **updates)
        
        # Update workpad test status
        test_run = self.state_manager.get_test_run(run_id)
        if test_run and test_run.workpad_id:
            workpad = self.git_engine.get_workpad(test_run.workpad_id)
            if workpad:
                workpad.test_status = 'green' if status == 'passed' else 'red'
                self.git_engine._save_metadata()
    
    def get_test_runs(self, workpad_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get test runs for a workpad."""
        test_runs = self.state_manager.list_test_runs(workpad_id)
        return [tr.to_dict() for tr in test_runs]
    
    # AI Operations
    
    def create_ai_operation(self, workpad_id: Optional[str], 
                           operation_type: str,
                           model: str, 
                           prompt: str) -> Dict[str, Any]:
        """
        Track AI operation in state.
        
        Args:
            workpad_id: Workpad ID
            operation_type: Type (planning/coding/review)
            model: Model name
            prompt: User prompt
            
        Returns:
            AI operation info
        """
        operation = self.state_manager.create_ai_operation(
            workpad_id, operation_type, model, prompt
        )
        
        return operation.to_dict()
    
    def update_ai_operation(self, operation_id: str, 
                           status: str,
                           response: Optional[str] = None,
                           cost_usd: Optional[float] = None) -> None:
        """
        Update AI operation state.
        
        Args:
            operation_id: Operation ID
            status: New status
            response: AI response
            cost_usd: Cost in USD
        """
        updates = {'status': status}
        
        if response is not None:
            updates['response'] = response
        
        if cost_usd is not None:
            updates['cost_usd'] = cost_usd
        
        if status in ['completed', 'failed']:
            updates['completed_at'] = datetime.utcnow().isoformat()
        
        self.state_manager.update_ai_operation(operation_id, **updates)
    
    def list_ai_operations(self, workpad_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List AI operations for a workpad.
        
        Args:
            workpad_id: Optional workpad ID to filter by
            
        Returns:
            List of AI operation dictionaries
        """
        operations = self.state_manager.list_ai_operations(workpad_id)
        return [op.to_dict() for op in operations]
    
    # Git Operations
    
    def get_status(self, repo_id: str, pad_id: Optional[str] = None) -> Dict[str, Any]:
        """Get git status for repo/workpad."""
        return self.git_engine.get_status(repo_id, pad_id)
    
    def get_history(self, repo_id: str, branch: Optional[str] = None, 
                    limit: int = 20) -> List[Dict[str, Any]]:
        """Get commit history with normalized field names."""
        commits = self.git_engine.get_history(repo_id, limit, branch)
        
        # Normalize field names for consistency
        normalized = []
        for commit in commits:
            normalized.append({
                'sha': commit.get('hash', commit.get('sha', '')),
                'short_sha': commit.get('short_hash', commit.get('short_sha', commit.get('hash', '')[:8])),
                'message': commit.get('message', ''),
                'author': commit.get('author', ''),
                'timestamp': commit.get('date', commit.get('timestamp', '')),
                'parents': commit.get('parents', [])
            })
        
        return normalized
    
    def get_diff(self, pad_id: str, base: str = "trunk") -> str:
        """Get diff for workpad."""
        return self.git_engine.get_diff(pad_id, base)
    
    def revert_last_commit(self, repo_id: str) -> None:
        """Revert last commit on trunk."""
        self.git_engine.revert_last_commit(repo_id)
        self._sync_commits(repo_id)
    
    # State Synchronization
    
    def _sync_commits(self, repo_id: str, limit: int = 100) -> None:
        """
        Sync commits from git to state manager.
        
        Args:
            repo_id: Repository ID
            limit: Maximum commits to sync
        """
        # Get commits from git
        commits = self.git_engine.get_history(repo_id, limit=limit)
        
        # Add to state manager
        for commit in commits:
            sha = commit.get('hash', commit.get('sha', ''))
            parents = commit.get('parents', [])
            parent_sha = parents[0] if parents else None
            
            commit_node = CommitNode(
                sha=sha,
                short_sha=sha[:8] if sha else '',
                message=commit.get('message', ''),
                author=commit.get('author', ''),
                timestamp=commit.get('date', commit.get('timestamp', '')),
                parent_sha=parent_sha,
                is_trunk=True  # Commits from history are trunk commits
            )
            self.state_manager.add_commit(repo_id, commit_node)
    
    def sync_all(self) -> Dict[str, int]:
        """
        Sync all state from git engine to state manager.
        
        Returns:
            Statistics of synced items
        """
        logger.info("Starting full state sync")
        
        stats = {
            'repos': 0,
            'workpads': 0,
            'commits': 0
        }
        
        # Sync repositories
        for repo in self.git_engine.list_repos():
            repo_state = self.state_manager.get_repository(repo.id)
            if not repo_state:
                self.state_manager.create_repository(
                    repo_id=repo.id,
                    name=repo.name,
                    path=str(repo.path)
                )
                stats['repos'] += 1
            
            # Sync commits
            self._sync_commits(repo.id)
            stats['commits'] += len(self.state_manager.get_commits(repo.id))
            
            # Sync workpads
            for workpad in self.git_engine.list_workpads(repo.id):
                workpad_state = self.state_manager.get_workpad(workpad.id)
                if not workpad_state:
                    self.state_manager.create_workpad(
                        workpad_id=workpad.id,
                        repo_id=workpad.repo_id,
                        title=workpad.title,
                        branch_name=workpad.branch_name,
                        base_commit=workpad.last_commit or "HEAD"
                    )
                    stats['workpads'] += 1
        
        logger.info(f"Sync complete: {stats}")
        return stats
    
    def get_active_context(self) -> Dict[str, Optional[str]]:
        """Get active repository and workpad."""
        return self.state_manager.get_active_context()
    
    def set_active_context(self, repo_id: Optional[str] = None, 
                          workpad_id: Optional[str] = None) -> None:
        """Set active repository and/or workpad."""
        self.state_manager.set_active_context(repo_id, workpad_id)
