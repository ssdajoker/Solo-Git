
"""
AI Orchestration Layer for Solo Git.

This package provides intelligent AI model routing, cost management,
and multi-model orchestration capabilities.
"""

from sologit.orchestration.model_router import ModelRouter, ModelConfig, ModelTier
from sologit.orchestration.cost_guard import CostGuard, CostTracker, BudgetConfig
from sologit.orchestration.ai_orchestrator import AIOrchestrator, PlanResponse, PatchResponse
from sologit.orchestration.planning_engine import PlanningEngine, CodePlan
from sologit.orchestration.code_generator import CodeGenerator, GeneratedPatch

__all__ = [
    'ModelRouter',
    'ModelConfig',
    'ModelTier',
    'CostGuard',
    'CostTracker',
    'BudgetConfig',
    'AIOrchestrator',
    'PlanResponse',
    'PatchResponse',
    'PlanningEngine',
    'CodePlan',
    'CodeGenerator',
    'GeneratedPatch',
]

