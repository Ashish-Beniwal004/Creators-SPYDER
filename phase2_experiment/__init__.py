"""
Phase 2E Experimental Integration and Pilot Validation Package
Project: Evidence-Grounded Agentic Criminal Network Investigation
Module: phase2_experiment
"""

from phase2_experiment.config import (
    DEFAULT_TOP_K,
    PIPELINE_METADATA,
    FROZEN_HASHES,
)
from phase2_experiment.schemas import (
    SystemCaseOutput,
    ArmRunResult,
    PilotRunManifest,
    PilotScoringReport,
)
from phase2_experiment.system_a import run_system_a
from phase2_experiment.system_b import run_system_b
from phase2_experiment.runner import run_pilot_experiment
from phase2_experiment.evaluator import evaluate_pilot_runs

__all__ = [
    "run_system_a",
    "run_system_b",
    "run_pilot_experiment",
    "evaluate_pilot_runs",
    "SystemCaseOutput",
    "ArmRunResult",
    "PilotRunManifest",
    "PilotScoringReport",
    "DEFAULT_TOP_K",
    "PIPELINE_METADATA",
    "FROZEN_HASHES",
]
