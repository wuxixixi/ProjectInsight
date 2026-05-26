"""
Global Constants Definition

This module has no dependencies on other backend modules and can be safely imported anywhere.
"""

# Opinion classification thresholds (unified, ensures cross-module consistency)
OPINION_THRESHOLD_NEGATIVE = -0.1  # Below this value indicates misled belief
OPINION_THRESHOLD_POSITIVE = 0.1   # Above this value indicates correct belief

# Polarization thresholds (for identifying extreme views, stricter than normal classification)
# issue #962: Centralized management, distinct from OPINION_THRESHOLD semantics
POLARIZATION_THRESHOLD_NEGATIVE = -0.3  # Extreme negative stance (radical belief)
POLARIZATION_THRESHOLD_POSITIVE = 0.3   # Extreme positive stance (radical belief)
