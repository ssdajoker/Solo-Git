
"""
Code Generator for AI-driven patch generation.

Generates code patches from implementation plans.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional, Dict, Any
from pathlib import Path

from sologit.api.client import AbacusClient, ChatMessage, AbacusAPIError

if TYPE_CHECKING:
    from sologit.api.client import ChatResponse
from sologit.orchestration.planning_engine import CodePlan
from sologit.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class GeneratedPatch:
    """A generated code patch."""
    diff: str
    files_changed: List[str]
    additions: int
    deletions: int
    model: str
    confidence: float = 0.0  # 0.0 to 1.0
    
    def __str__(self) -> str:
        """Human-readable summary."""
        return (
            f"Patch: {len(self.files_changed)} files changed, "
            f"+{self.additions} -{self.deletions} lines"
        )


class CodeGenerator:
    """
    Generates code patches from implementation plans.
    """
    
    CODING_SYSTEM_PROMPT = """You are an expert software developer working on Solo Git, an AI-native version control system.

Your role is to generate clean, well-structured code patches based on implementation plans.

Follow these guidelines:
1. Write idiomatic, readable code
2. Follow existing code style and conventions
3. Include docstrings and comments
4. Handle errors appropriately
5. Write code that is testable
6. Generate unified diff format patches

For Python code:
- Use type hints
- Follow PEP 8
- Use pathlib for file operations
- Use dataclasses where appropriate

Generate patches in unified diff format. For new files, use /dev/null as the source.

Example patch format:
```diff
--- a/path/to/file.py
+++ b/path/to/file.py
@@ -1,5 +1,7 @@
 def existing_function():
     # existing code
+    # new code
+    new_line()
```

Only output the patch itself, no explanatory text outside the diff."""
    
    def __init__(self, client: AbacusClient):
        """
        Initialize code generator.

        Args:
            client: Abacus.ai API client
        """
        self.client = client
        self.last_response: Optional['ChatResponse'] = None
        logger.info("CodeGenerator initialized")
    
    def generate_patch(
        self,
        task_description: str = None,
        plan: Optional[str] = None,
        file_contents: Optional[Dict[str, str]] = None,
        model_config: Optional[Any] = None,
        client: Optional[Any] = None,
        deployment_credentials: Optional[Dict[str, str]] = None,
        # Legacy parameters for backward compatibility
        model: str = "deepseek-coder-33b",
        deployment_name: Optional[str] = None,
        deployment_id: Optional[str] = None,
        deployment_token: Optional[str] = None
    ) -> GeneratedPatch:
        """
        Generate a code patch from a task description or implementation plan.
        
        Args:
            task_description: Description of the task (new API)
            plan: Optional execution plan as string (new API)
            file_contents: Contents of existing files to modify
            model_config: Model configuration object (new API)
            client: AbacusClient instance (new API)
            deployment_credentials: Deployment credentials dict (new API)
            model: Model name (legacy API)
            deployment_name: Deployment name (legacy API)
            deployment_id: Deployment ID (legacy API)
            deployment_token: Deployment token (legacy API)
        
        Returns:
            Generated patch
        """
        # Handle both new and legacy API
        if task_description and isinstance(task_description, str):
            # New API: task_description and optional plan string
            logger.info("Generating patch for: %s", task_description[:50] if len(task_description) > 50 else task_description)
            context_parts = [f"Task: {task_description}"]
            if plan:
                context_parts.append(f"\nPlan:\n{plan}")
        else:
            # Legacy API: first parameter is actually a CodePlan object
            plan_obj = task_description  # It's actually a CodePlan
            logger.info("Generating patch for: %s", plan_obj.title)
            context_parts = [
                f"Implementation Plan: {plan_obj.title}",
                f"\n{plan_obj.description}",
                "\nFile Changes:"
            ]
            
            for fc in plan_obj.file_changes:
                context_parts.append(f"  - {fc.action.upper()}: {fc.path}")
                context_parts.append(f"    Reason: {fc.reason}")
                
                # Include existing file content if available
                if fc.action == 'modify' and file_contents and fc.path in file_contents:
                    content = file_contents[fc.path]
                    # Truncate if too long
                    if len(content) > 2000:
                        content = content[:2000] + "\n... (truncated)"
                    context_parts.append(f"    Current content:\n```\n{content}\n```")
            
            context_parts.append(f"\nTest Strategy: {plan_obj.test_strategy}")
        
        # Add file contents for new API
        if file_contents and isinstance(task_description, str):
            context_parts.append("\nExisting Files:")
            for path, content in file_contents.items():
                if len(content) > 2000:
                    content = content[:2000] + "\n... (truncated)"
                context_parts.append(f"  {path}:\n```\n{content}\n```")
        
        context_parts.append("\nGenerate a unified diff patch that implements this plan.")
        context_message = "\n".join(context_parts)
        
        # Create chat messages
        messages = [
            ChatMessage(role="system", content=self.CODING_SYSTEM_PROMPT),
            ChatMessage(role="user", content=context_message)
        ]
        
        # For Phase 2 without full deployment setup, use mock generation
        self.last_response = None
        
        # Determine which client and credentials to use
        api_client = client if client else self.client
        model_name = model_config.name if model_config else model
        
        # Extract deployment credentials from new or legacy API
        if deployment_credentials:
            deploy_name = deployment_credentials.get('deployment_name')
            deploy_id = deployment_credentials.get('deployment_id')
            deploy_token = deployment_credentials.get('deployment_token')
        else:
            deploy_name = deployment_name
            deploy_id = deployment_id
            deploy_token = deployment_token

        try:
            if deploy_name or (deploy_id and deploy_token):
                response = api_client.chat(
                    messages=messages,
                    model=model_name,
                    max_tokens=2048,
                    temperature=0.1,
                    deployment=deploy_name,
                    deployment_id=deploy_id,
                    deployment_token=deploy_token
                )
                self.last_response = response
                diff = self._extract_diff(response.content)
            else:
                # Mock patch generation for Phase 2 development
                logger.warning("No deployment credentials provided, using mock patch")
                # For new API, use task_description; for legacy API, use the plan object
                if isinstance(task_description, str):
                    diff = self._generate_mock_patch_from_description(task_description, plan, file_contents)
                else:
                    diff = self._generate_mock_patch(task_description, file_contents)
            
            # Analyze the patch
            files_changed = self._extract_files_from_diff(diff)
            additions, deletions = self._count_changes(diff)
            
            patch = GeneratedPatch(
                diff=diff,
                files_changed=files_changed,
                additions=additions,
                deletions=deletions,
                model=model,
                confidence=0.8  # Mock confidence
            )
            
            logger.info("Generated patch: %s", patch)
            return patch
            
        except AbacusAPIError:
            self.last_response = None
            raise
        except Exception as e:
            logger.error("Failed to generate patch: %s", e)
            # Return a minimal patch
            return self._create_fallback_patch(plan)
    
    def _extract_diff(self, content: str) -> str:
        """Extract diff from AI response."""
        # Remove markdown code blocks if present
        content = content.strip()
        
        if '```diff' in content:
            import re
            match = re.search(r'```diff\n(.*?)\n```', content, re.DOTALL)
            if match:
                return match.group(1).strip()
        
        if '```' in content:
            import re
            match = re.search(r'```\n(.*?)\n```', content, re.DOTALL)
            if match:
                return match.group(1).strip()
        
        # If no code blocks, look for diff markers
        lines = content.split('\n')
        diff_lines = []
        in_diff = False
        
        for line in lines:
            if line.startswith('---') or line.startswith('+++') or line.startswith('@@'):
                in_diff = True
            if in_diff:
                diff_lines.append(line)
        
        if diff_lines:
            return '\n'.join(diff_lines)
        
        # Return as-is if we can't parse
        return content
    
    def _extract_files_from_diff(self, diff: str) -> List[str]:
        """Extract list of files from a diff."""
        files = []
        for line in diff.split('\n'):
            if line.startswith('--- '):
                file_path = line[4:].strip()
                if file_path != '/dev/null' and file_path.startswith('a/'):
                    files.append(file_path[2:])
            elif line.startswith('+++ '):
                file_path = line[4:].strip()
                if file_path != '/dev/null' and file_path.startswith('b/'):
                    file_path = file_path[2:]
                    if file_path not in files:
                        files.append(file_path)
        return files
    
    def _count_changes(self, diff: str) -> tuple:
        """Count additions and deletions in a diff."""
        additions = 0
        deletions = 0
        
        for line in diff.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                additions += 1
            elif line.startswith('-') and not line.startswith('---'):
                deletions += 1
        
        return additions, deletions
    
    def _generate_mock_patch_from_description(
        self,
        task_description: str,
        plan: Optional[str],
        file_contents: Optional[Dict[str, str]]
    ) -> str:
        """Generate a mock patch from task description for development/testing."""
        # Simple mock patch for testing
        patch = "--- a/test.py\n"
        patch += "+++ b/test.py\n"
        patch += "@@ -1,3 +1,6 @@\n"
        patch += " # Existing code\n"
        patch += f"+# Mock implementation for: {task_description[:50]}\n"
        patch += "+# TODO: Implement actual changes\n"
        patch += "+\n"
        patch += " # More existing code\n"
        return patch
    
    def _generate_mock_patch(
        self,
        plan: CodePlan,
        file_contents: Optional[Dict[str, str]]
    ) -> str:
        """Generate a mock patch for development/testing."""
        patches = []
        
        for fc in plan.file_changes:
            if fc.action == 'create':
                # Generate a new file patch
                content_lines = [
                    '"""',
                    f'Module: {Path(fc.path).stem}',
                    '',
                    fc.reason,
                    '"""',
                    '',
                    '# TODO: Implement this module',
                    '',
                ]
                
                patch = "--- /dev/null\n"
                patch += f"+++ b/{fc.path}\n"
                patch += f"@@ -0,0 +1,{len(content_lines)} @@\n"
                patch += '\n'.join(f'+{line}' for line in content_lines)
                patches.append(patch)
                
            elif fc.action == 'modify':
                # Generate a modification patch
                # This is a simplified mock - real patches would be more sophisticated
                patch = f"--- a/{fc.path}\n"
                patch += f"+++ b/{fc.path}\n"
                patch += "@@ -1,5 +1,8 @@\n"
                patch += " # Existing code\n"
                patch += f"+# Added: {fc.reason}\n"
                patch += f"+# TODO: Implement changes for: {plan.title}\n"
                patch += "+\n"
                patch += " # More existing code\n"
                patches.append(patch)
                
            elif fc.action == 'delete':
                # Generate a deletion patch
                patch = f"--- a/{fc.path}\n"
                patch += "+++ /dev/null\n"
                patch += "@@ -1,10 +0,0 @@\n"
                patch += "-# File deleted\n"
                patches.append(patch)
        
        return '\n\n'.join(patches)
    
    def _create_fallback_patch(self, plan: CodePlan) -> GeneratedPatch:
        """Create a minimal fallback patch when generation fails."""
        # Create a simple TODO patch
        diff = "--- a/TODO.md\n"
        diff += "+++ b/TODO.md\n"
        diff += "@@ -1,1 +1,3 @@\n"
        diff += f"+# TODO: {plan.title}\n"
        diff += f"+{plan.description[:100]}\n"
        diff += "+\n"
        
        return GeneratedPatch(
            diff=diff,
            files_changed=['TODO.md'],
            additions=3,
            deletions=0,
            model="fallback",
            confidence=0.1
        )
    
    def generate_patch_from_feedback(
        self,
        original_patch: GeneratedPatch,
        feedback: str,
        model: str = "deepseek-coder-33b",
        deployment_id: Optional[str] = None,
        deployment_token: Optional[str] = None
    ) -> GeneratedPatch:
        """
        Refine a patch based on feedback (e.g., from test failures).
        
        Args:
            original_patch: The original patch
            feedback: Feedback or error messages
            model: Model to use
            deployment_id: Deployment ID
            deployment_token: Deployment token
        
        Returns:
            Refined patch
        """
        logger.info("Refining patch based on feedback")
        
        # For Phase 2, return the original patch (no refinement yet)
        logger.warning("Patch refinement not fully implemented in Phase 2")
        return original_patch

