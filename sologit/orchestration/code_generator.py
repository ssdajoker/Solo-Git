
"""
Code Generator for AI-driven patch generation.

Generates code patches from implementation plans.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional, Dict, Any
from pathlib import Path
from difflib import unified_diff
import re

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
        plan: Optional[Any] = None,
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
        plan_obj: Optional[CodePlan] = None
        plan_text: Optional[str] = plan if isinstance(plan, str) else None
        description_text: Optional[str] = None

        if isinstance(task_description, CodePlan):
            plan_obj = task_description
        elif isinstance(task_description, str):
            description_text = task_description

        if plan_obj is None and isinstance(plan, CodePlan):
            plan_obj = plan

        if plan_obj:
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
        else:
            task_text = description_text or plan_text or "Generated task"
            logger.info(
                "Generating patch for: %s",
                task_text[:50] if len(task_text) > 50 else task_text
            )
            context_parts = [f"Task: {task_text}"]
            if plan_text:
                context_parts.append(f"\nPlan:\n{plan_text}")
        
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
                if not plan_obj:
                    diff = self._generate_mock_patch_from_description(
                        description_text or plan_text or "Generated task",
                        plan_text,
                        file_contents
                    )
                else:
                    diff = self._generate_mock_patch(plan_obj, file_contents)
            
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
            return self._create_fallback_patch(plan_obj, description_text or plan_text)
    
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
        """Generate a deterministic scaffold patch from a task description."""
        description = plan or task_description or "generated task"
        target_path: str
        existing_content = ""

        if file_contents:
            # Prefer updating the first provided file to keep deterministic behaviour.
            target_path, existing_content = next(iter(file_contents.items()))
        else:
            target_path = "mock_task.py"

        stub_name = self._build_stub_name(target_path, description)
        stub_block = self._create_function_stub(stub_name, description)

        if target_path.endswith(".py") and not file_contents:
            module_header = self._create_module_header(description)
        else:
            module_header = ""

        if not existing_content:
            new_content = f"{module_header}{stub_block}"
        else:
            new_content = self._append_stub_to_content(existing_content, stub_block)

        return self._build_diff(
            target_path,
            existing_content,
            new_content,
            is_new_file=not existing_content,
            is_delete=False
        )

    def _generate_mock_patch(
        self,
        plan: CodePlan,
        file_contents: Optional[Dict[str, str]]
    ) -> str:
        """Generate a mock patch for development/testing."""
        patches = []

        for index, fc in enumerate(plan.file_changes):
            reason = fc.reason or plan.title
            existing_content = ""
            if file_contents and fc.path in file_contents:
                existing_content = file_contents[fc.path]

            stub_name = self._build_stub_name(fc.path, reason, index)
            stub_block = self._create_function_stub(stub_name, reason)

            if fc.action == 'create':
                module_header = self._create_module_header(reason)
                new_content = f"{module_header}{stub_block}"
                patch = self._build_diff(
                    fc.path,
                    "",
                    new_content,
                    is_new_file=True,
                    is_delete=False
                )
                patches.append(patch)

            elif fc.action == 'modify':
                if existing_content:
                    new_content = self._append_stub_to_content(existing_content, stub_block)
                    patch = self._build_diff(
                        fc.path,
                        existing_content,
                        new_content,
                        is_new_file=False,
                        is_delete=False
                    )
                else:
                    module_header = self._create_module_header(reason) if fc.path.endswith('.py') else ""
                    new_content = f"{module_header}{stub_block}"
                    patch = self._build_diff(
                        fc.path,
                        "",
                        new_content,
                        is_new_file=False,
                        is_delete=False
                    )
                patches.append(patch)

            elif fc.action == 'delete':
                patch = self._build_diff(
                    fc.path,
                    existing_content,
                    "",
                    is_new_file=False,
                    is_delete=True
                )
                if not patch:
                    patch = self._build_static_deletion_patch(fc.path)
                patches.append(patch)

        return '\n\n'.join(filter(None, patches))

    def _build_stub_name(self, reference: str, description: str, index: int = 0) -> str:
        """Create a deterministic stub function name based on file and description."""
        base_reference = Path(reference).stem or reference
        tokens = re.findall(r"[A-Za-z0-9]+", f"{base_reference} {description}")
        if not tokens:
            tokens = ["generated", "stub"]
        deduped_tokens: List[str] = []
        seen = set()
        for token in tokens:
            lower = token.lower()
            if lower not in seen:
                seen.add(lower)
                deduped_tokens.append(lower)
            if len(deduped_tokens) == 5:
                break
        if not deduped_tokens:
            deduped_tokens = ["generated", "stub"]
        name = "_".join(deduped_tokens)
        if not name.endswith("_stub"):
            name = f"{name}_stub"
        if name and name[0].isdigit():
            name = f"stub_{name}"
        if index:
            name = f"{name}_{index}"
        return name

    def _create_function_stub(self, function_name: str, description: str) -> str:
        """Return a function stub block."""
        safe_description = description.replace('"', '\"')
        lines = [
            f"def {function_name}(*args, **kwargs) -> None:",
            f"    \"\"\"Placeholder for {safe_description}.\"\"\"",
            "    raise NotImplementedError(\"Auto-generated stub\")",
            "",
        ]
        return "\n".join(lines)

    def _create_module_header(self, description: str) -> str:
        """Create a simple module-level docstring."""
        safe_description = description.replace('"', '\"')
        return f'"""Auto-generated scaffold for {safe_description}."""\n\n'

    def _append_stub_to_content(self, existing_content: str, stub_block: str) -> str:
        """Append a stub block to existing content with spacing.
        
        Ensures that there is at least one blank line between the existing content
        and the appended stub block, but avoids adding excessive blank lines.
        """
        content = existing_content or ""
        if content and not content.endswith("\n"):
            content += "\n"
        # If content is not empty and does not end with two newlines, add one newline as separator.
        if not content:
            separator = ""
        elif not content.endswith("\n\n"):
            separator = "\n"
        else:
            separator = ""
        new_content = f"{content}{separator}{stub_block}"
        if not new_content.endswith("\n"):
            new_content += "\n"
        return new_content

    def _build_diff(
        self,
        path: str,
        original_content: str,
        new_content: str,
        *,
        is_new_file: bool,
        is_delete: bool
    ) -> str:
        """Create a unified diff between two content versions."""
        original_lines = original_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        from_label = "/dev/null" if is_new_file else f"a/{path}"
        to_label = "/dev/null" if is_delete else f"b/{path}"

        diff_lines = list(
            unified_diff(
                original_lines,
                new_lines,
                fromfile=from_label,
                tofile=to_label,
                lineterm=""
            )
        )
        return "\n".join(diff_lines)

    def _build_static_deletion_patch(self, path: str) -> str:
        """Fallback deletion patch when original content is unavailable."""
        return (
            f"--- a/{path}\n"
            "+++ /dev/null\n"
            "@@ -1 +0,0 @@\n"
            "-# Auto-generated placeholder\n"
        )
    
    def _create_fallback_patch(
        self,
        plan: Optional[CodePlan],
        description: Optional[str] = None
    ) -> GeneratedPatch:
        """Create a minimal fallback patch when generation fails."""
        title = plan.title if plan else (description or "Generated task")
        summary = plan.description if plan else (description or "No description provided")

        diff = "--- a/TODO.md\n"
        diff += "+++ b/TODO.md\n"
        diff += "@@ -1,1 +1,3 @@\n"
        diff += f"+# TODO: {title}\n"
        diff += f"+{summary[:100]}\n"
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

