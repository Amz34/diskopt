"""
diskopt package initialization.
"""

from diskopt.engine import get_disk_metric, scan_reclaimable, verify_guardrail

__version__ = "1.0.0"
__all__ = ["get_disk_metric", "scan_reclaimable", "verify_guardrail"]
