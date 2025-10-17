
"""
Planning Engine for AI-driven code planning.

Analyzes prompts and generates detailed implementation plans.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path

from sologit.api.client import AbacusClient, ChatMessage
from sologit.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FileChange:
    """Represents a planned file change."""
    path: str
    action: str  # 'create', 'modify', 'delete'
    reason: str
    estimated_lines: int = 0


@dataclass
class CodePlan:
    """Detailed implementation plan."""
    title: str
    description: str
    file_changes: List[FileChange]
    test_strategy: str
    risks: List[str]
    dependencies: List[str] = field(default_factory=list)
    estimated_complexity: str = "medium"  # 'low', 'medium', 'high'
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'title': self.title,
            'description': self.description,
            'file_changes': [
                {
                    'path': fc.path,
                    'action': fc.action,
                    'reason': fc.reason,
                    'estimated_lines': fc.estimated_lines
                }
                for fc in self.file_changes
            ],
            'test_strategy': self.test_strategy,
            'risks': self.risks,
            'dependencies': self.dependencies,
            'estimated_complexity': self.estimated_complexity
        }
    
    def __str__(self) -> str:
        """Human-readable representation."""
        lines = [
            f"# {self.title}",
            "",
            self.description,
            "",
            "## File Changes:",
        ]
        
        for fc in self.file_changes:
            lines.append(f"  - {fc.action.upper()}: {fc.path}")
            lines.append(f"    Reason: {fc.reason}")
            if fc.estimated_lines > 0:
                lines.append(f"    Est. lines: {fc.estimated_lines}")
        
        lines.extend([
            "",
            "## Test Strategy:",
            f"  {self.test_strategy}",
            "",
            "## Risks:",
        ])
        
        for risk in self.risks:
            lines.append(f"  - {risk}")
        
        if self.dependencies:
            lines.extend([
                "",
                "## Dependencies:",
            ])
            for dep in self.dependencies:
                lines.append(f"  - {dep}")
        
        lines.extend([
            "",
            f"## Complexity: {self.estimated_complexity.upper()}"
        ])
        
        return "\n".join(lines)


class PlanningEngine:
    """
    Generates detailed implementation plans from user prompts.
    """
    
    PLANNING_SYSTEM_PROMPT = """You are an expert software architect and planner for Solo Git, an AI-native version control system.

Your role is to analyze user requests and create detailed, actionable implementation plans.

For each request, you should:
1. Understand the intent and scope
2. Identify which files need to be created, modified, or deleted
3. Plan the implementation strategy
4. Consider testing requirements
5. Identify potential risks and dependencies

Respond with a structured JSON plan in this format:
{
  "title": "Brief title for the change",
  "description": "Detailed description of what will be implemented and how",
  "file_changes": [
    {
      "path": "path/to/file.py",
      "action": "create|modify|delete",
      "reason": "Why this file needs to be changed",
      "estimated_lines": 50
    }
  ],
  "test_strategy": "How this change should be tested",
  "risks": ["Potential risk 1", "Potential risk 2"],
  "dependencies": ["External dependency 1"],
  "estimated_complexity": "low|medium|high"
}

Be specific, practical, and consider the existing codebase structure."""
    
    def __init__(self, client: AbacusClient):
        """
        Initialize planning engine.
        
        Args:
            client: Abacus.ai API client
        """
        self.client = client
        logger.info("PlanningEngine initialized")
    
    def generate_plan(
        self,
        prompt: str,
        repo_context: Optional[Dict[str, Any]] = None,
        model: str = "gpt-4o",
        deployment_id: Optional[str] = None,
        deployment_token: Optional[str] = None
    ) -> CodePlan:
        """
        Generate an implementation plan from a user prompt.
        
        Args:
            prompt: User's request
            repo_context: Context about the repository (file tree, recent changes, etc.)
            model: Model to use for planning
            deployment_id: Abacus.ai deployment ID (if using chat API)
            deployment_token: Deployment token (if using chat API)
        
        Returns:
            Generated code plan
        """
        logger.info("Generating plan for: %s", prompt[:100])
        
        # Build context message
        context_parts = [f"User request: {prompt}"]
        
        if repo_context:
            if 'file_tree' in repo_context:
                context_parts.append(
                    f"\nRepository structure:\n{self._format_file_tree(repo_context['file_tree'])}"
                )
            
            if 'recent_changes' in repo_context:
                context_parts.append(
                    f"\nRecent changes:\n{repo_context['recent_changes']}"
                )
            
            if 'language' in repo_context:
                context_parts.append(f"\nPrimary language: {repo_context['language']}")
        
        context_message = "\n".join(context_parts)
        
        # Create chat messages
        messages = [
            ChatMessage(role="system", content=self.PLANNING_SYSTEM_PROMPT),
            ChatMessage(role="user", content=context_message)
        ]
        
        # For Phase 2 without full deployment setup, we'll use a mock response
        # In production, this would call the actual API
        try:
            if deployment_id and deployment_token:
                response = self.client.chat(
                    messages=messages,
                    model=model,
                    max_tokens=4096,
                    temperature=0.2,
                    deployment_id=deployment_id,
                    deployment_token=deployment_token
                )
                plan_data = self._parse_plan_response(response.content)
            else:
                # Mock response for Phase 2 development
                logger.warning("No deployment credentials provided, using mock plan")
                plan_data = self._generate_mock_plan(prompt, repo_context)
            
            # Create CodePlan object
            plan = CodePlan(
                title=plan_data.get('title', 'Implementation Plan'),
                description=plan_data.get('description', ''),
                file_changes=[
                    FileChange(**fc) for fc in plan_data.get('file_changes', [])
                ],
                test_strategy=plan_data.get('test_strategy', 'Add unit tests'),
                risks=plan_data.get('risks', []),
                dependencies=plan_data.get('dependencies', []),
                estimated_complexity=plan_data.get('estimated_complexity', 'medium')
            )
            
            logger.info("Generated plan with %d file changes", len(plan.file_changes))
            return plan
            
        except Exception as e:
            logger.error("Failed to generate plan: %s", e)
            # Return a basic fallback plan
            return self._create_fallback_plan(prompt)
    
    def _format_file_tree(self, file_tree: Any) -> str:
        """Format file tree for context."""
        if isinstance(file_tree, list):
            return "\n".join(f"  - {item}" for item in file_tree[:20])  # Limit to 20 files
        return str(file_tree)[:500]  # Limit size
    
    def _parse_plan_response(self, content: str) -> Dict:
        """Parse the AI response into a plan dictionary."""
        import json
        
        # Try to extract JSON from the response
        # Handle cases where response is wrapped in markdown code blocks
        content = content.strip()
        
        if content.startswith('```json'):
            content = content[7:]
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
        
        content = content.strip()
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse plan JSON: %s", e)
            # Try to extract JSON-like content
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except:
                    pass
            
            # Return minimal structure
            return {
                'title': 'Implementation Plan',
                'description': content[:500],
                'file_changes': [],
                'test_strategy': 'Add tests',
                'risks': [],
                'estimated_complexity': 'medium'
            }
    
    def _generate_mock_plan(
        self,
        prompt: str,
        repo_context: Optional[Dict[str, Any]]
    ) -> Dict:
        """Generate a mock plan for development/testing."""
        # Simple keyword-based mock planning
        prompt_lower = prompt.lower()
        
        file_changes = []
        
        # Detect what kind of change is being requested
        if 'add' in prompt_lower or 'create' in prompt_lower or 'implement' in prompt_lower:
            # Adding new functionality
            if 'test' in prompt_lower:
                file_changes.append({
                    'path': 'tests/test_new_feature.py',
                    'action': 'create',
                    'reason': 'Add tests for new functionality',
                    'estimated_lines': 50
                })
            
            # Guess at file location based on keywords
            if 'api' in prompt_lower or 'endpoint' in prompt_lower:
                file_changes.append({
                    'path': 'sologit/api/endpoints.py',
                    'action': 'modify',
                    'reason': 'Add new API endpoint',
                    'estimated_lines': 30
                })
            elif 'cli' in prompt_lower or 'command' in prompt_lower:
                file_changes.append({
                    'path': 'sologit/cli/commands.py',
                    'action': 'modify',
                    'reason': 'Add new CLI command',
                    'estimated_lines': 40
                })
            else:
                file_changes.append({
                    'path': 'sologit/core/new_feature.py',
                    'action': 'create',
                    'reason': 'Implement new feature',
                    'estimated_lines': 100
                })
        
        elif 'fix' in prompt_lower or 'bug' in prompt_lower:
            file_changes.append({
                'path': 'sologit/core/module.py',
                'action': 'modify',
                'reason': 'Fix reported bug',
                'estimated_lines': 20
            })
        
        elif 'refactor' in prompt_lower or 'improve' in prompt_lower:
            file_changes.append({
                'path': 'sologit/core/module.py',
                'action': 'modify',
                'reason': 'Refactor for better code quality',
                'estimated_lines': 50
            })
        
        # Default if no changes detected
        if not file_changes:
            file_changes.append({
                'path': 'sologit/core/module.py',
                'action': 'modify',
                'reason': 'Implement requested changes',
                'estimated_lines': 50
            })
        
        return {
            'title': prompt[:60],
            'description': f"Implementation plan for: {prompt}\n\nThis is a mock plan generated for Phase 2 development. In production, this would be generated by the AI planning model.",
            'file_changes': file_changes,
            'test_strategy': 'Add unit tests to verify the changes work correctly. Run existing test suite to ensure no regressions.',
            'risks': [
                'May affect existing functionality',
                'Need to ensure backward compatibility'
            ],
            'dependencies': [],
            'estimated_complexity': 'medium'
        }
    
    def _create_fallback_plan(self, prompt: str) -> CodePlan:
        """Create a minimal fallback plan when planning fails."""
        return CodePlan(
            title="Basic Implementation",
            description=f"Implement: {prompt}",
            file_changes=[
                FileChange(
                    path="module.py",
                    action="modify",
                    reason="Implement requested changes",
                    estimated_lines=50
                )
            ],
            test_strategy="Add tests after implementation",
            risks=["Planning failed, proceeding with basic approach"],
            estimated_complexity="unknown"
        )

