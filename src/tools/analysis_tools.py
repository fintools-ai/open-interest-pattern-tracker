"""
Analysis Tools - Wraps existing analysis utility methods
"""

import logging
from typing import Dict, Any, List

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_pipeline.delta_calculator import DeltaCalculator

logger = logging.getLogger("oi_tracker.tools.analysis")


def detect_large_blocks(
    current_strikes: Dict[str, Any],
    previous_strikes: Dict[str, Any],
    threshold: int = 5000
) -> List[Dict[str, Any]]:
    """
    Detect unusually large OI increases that might indicate institutional activity.
    Wraps DeltaCalculator._detect_large_blocks()

    Args:
        current_strikes: Current strike data
        previous_strikes: Previous strike data
        threshold: Minimum OI increase to flag (default: 5000)

    Returns:
        List of large block detections
    """
    try:
        calculator = DeltaCalculator()
        blocks = calculator._detect_large_blocks(current_strikes, previous_strikes, threshold)
        logger.info(f"Detected {len(blocks)} large blocks")
        return blocks
    except Exception as e:
        logger.error(f"Failed to detect large blocks: {e}")
        return []


def detect_unusual_activity(
    current_oi: Dict[str, Any],
    previous_oi: Dict[str, Any]
) -> List[str]:
    """
    Flag unusual activity patterns.
    Wraps DeltaCalculator._detect_unusual_activity()

    Args:
        current_oi: Current OI data
        previous_oi: Previous OI data

    Returns:
        List of unusual activity flags
    """
    try:
        calculator = DeltaCalculator()
        flags = calculator._detect_unusual_activity(current_oi, previous_oi)
        logger.info(f"Detected {len(flags)} unusual activity flags")
        return flags
    except Exception as e:
        logger.error(f"Failed to detect unusual activity: {e}")
        return []


def find_new_strikes(
    current_strikes: Dict[str, int],
    previous_strikes: Dict[str, int]
) -> List[Dict[str, Any]]:
    """
    Find strikes that didn't exist in previous data.
    Wraps DeltaCalculator._find_new_strikes()

    Args:
        current_strikes: Current strike data
        previous_strikes: Previous strike data

    Returns:
        List of new strikes with OI values
    """
    try:
        calculator = DeltaCalculator()
        new_strikes = calculator._find_new_strikes(current_strikes, previous_strikes)
        logger.info(f"Found {len(new_strikes)} new strikes")
        return new_strikes
    except Exception as e:
        logger.error(f"Failed to find new strikes: {e}")
        return []
