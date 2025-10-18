"""
Tests for workflows.
"""

import pytest
from sologit.workflows.auto_merge import AutoMergeResult

def test_auto_merge_result_details_default():
    """
    Test that AutoMergeResult.details defaults to an empty list.

    This test confirms that the `details` field is initialized as an empty list.
    While the original implementation with `__post_init__` worked at runtime,
    using `field(default_factory=list)` is the idiomatic and type-safe way
    to handle mutable default values in dataclasses. This change prevents
    potential issues and improves code quality.
    """
    result = AutoMergeResult(success=False, pad_id="pad-123")
    assert result.details == []
    # The list should be a unique instance for each object
    result.details.append("a detail")

    result2 = AutoMergeResult(success=True, pad_id="pad-456")
    assert result2.details == []