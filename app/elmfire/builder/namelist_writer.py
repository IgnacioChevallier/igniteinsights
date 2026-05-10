"""
Generates the elmfire.data namelist file programmatically.

The namelist is a Fortran-style configuration file consumed directly by the
ELMFIRE binary. Field names correspond 1:1 to the mapping in docs/elmfire-mapping.md.

TODO Sprint siguiente: implement full namelist generation from raster metadata.
"""
from pathlib import Path


def write_namelist(config: dict, output_path: Path) -> Path:
    """Write an elmfire.data namelist from the given config dict."""
    raise NotImplementedError("namelist_writer: sprint siguiente")
