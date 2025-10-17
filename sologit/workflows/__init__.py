"""
Workflow orchestration for Solo Git.

Implements high-level workflows like auto-merge, CI integration, and rollback.
"""

from sologit.workflows.promotion_gate import PromotionGate, PromotionRules, PromotionDecision
from sologit.workflows.auto_merge import AutoMergeWorkflow
from sologit.workflows.ci_orchestrator import CIOrchestrator, CIResult
from sologit.workflows.rollback_handler import RollbackHandler

__all__ = [
    'PromotionGate',
    'PromotionRules',
    'PromotionDecision',
    'AutoMergeWorkflow',
    'CIOrchestrator',
    'CIResult',
    'RollbackHandler'
]
