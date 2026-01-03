"""
Backwards-compatible import path for the NetBox client.

Historically some code imported `pytbox.netbx`. The implementation lives in
`pytbox.nebtox` (typo kept for compatibility), so we re-export here.
"""

from .client import NetboxClient

__all__ = ["NetboxClient"]


