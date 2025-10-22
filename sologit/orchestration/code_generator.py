
"""
Code Generator for AI-driven patch generation.

Generates code patches from implementation plans.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pathlib import Path

from sologit.api.client import AbacusClient, ChatMessage, AbacusAPIError
from sologit.orchestration.planning_engine import CodePlan, FileChange
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
    
    def __init__(self, client: AbacusClient) -> None:
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
        plan: CodePlan,
        file_contents: Optional[Dict[str, str]] = None,
        model: str = "deepseek-coder-33b",
        deployment_name: Optional[str] = None,
        deployment_id: Optional[str] = None,
        deployment_token: Optional[str] = None
    ) -> GeneratedPatch:
        """
        Generate a code patch from an implementation plan.
        
        Args:
            plan: Implementation plan
            file_contents: Contents of existing files to modify
            model: Model to use for code generation
            deployment_id: Abacus.ai deployment ID (if using chat API)
            deployment_token: Deployment token (if using chat API)
        
        Returns:
            Generated patch
        """
        logger.info("Generating patch for: %s", plan.title)
        
        # Build context
        context_parts = [
            f"Implementation Plan: {plan.title}",
            f"\n{plan.description}",
            "\nFile Changes:"
        ]
        
        for fc in plan.file_changes:
            context_parts.append(f"  - {fc.action.upper()}: {fc.path}")
            context_parts.append(f"    Reason: {fc.reason}")
            
            # Include existing file content if available
            if fc.action == 'modify' and file_contents and fc.path in file_contents:
                content = file_contents[fc.path]
                # Truncate if too long
                if len(content) > 2000:
                    content = content[:2000] + "\n... (truncated)"
                context_parts.append(f"    Current content:\n```\n{content}\n```")
        
        context_parts.append(f"\nTest Strategy: {plan.test_strategy}")
        context_parts.append("\nGenerate a unified diff patch that implements this plan.")
        
        context_message = "\n".join(context_parts)
        
        # Create chat messages
        messages = [
            ChatMessage(role="system", content=self.CODING_SYSTEM_PROMPT),
            ChatMessage(role="user", content=context_message)
        ]
        
        # For Phase 2 without full deployment setup, use mock generation
        self.last_response = None

        try:
            if deployment_name or (deployment_id and deployment_token):
                response = self.client.chat(
                    messages=messages,
                    model=model,
                    max_tokens=2048,
                    temperature=0.1,
                    deployment=deployment_name,
                    deployment_id=deployment_id,
                    deployment_token=deployment_token
                )
                self.last_response = response
                diff = self._extract_diff(response.content)
            else:
                # Mock patch generation for Phase 2 development
                logger.warning("No deployment credentials provided, using mock patch")
                diff = self._generate_mock_patch(plan, file_contents)
            
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
                
                patch = f"--- /dev/null\n"
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
        diff = f"--- a/TODO.md\n"
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
        
        context = f"""Original patch:
```diff
{original_patch.diff}
```

Feedback/Errors:
{feedback}

Please generate an improved patch that addresses this feedback."""
        
        messages = [
            ChatMessage(role="system", content=self.CODING_SYSTEM_PROMPT),
            ChatMessage(role="user", content=context)
        ]
        
        # For Phase 2, return the original patch (no refinement yet)
        logger.warning("Patch refinement not fully implemented in Phase 2")
        return original_patch

