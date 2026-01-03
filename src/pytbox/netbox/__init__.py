"""
Backwards/alternative import path for the NetBox client.

Some users expect `pytbox.netbox`. The implementation lives in `pytbox.nebtox`,
so we re-export here.
"""

from .client import NetboxClient

__all__ = ["NetboxClient"]


