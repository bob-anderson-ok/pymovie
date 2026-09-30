"""Launch PymovieLcReader (a Go/Fyne app) on a .pymovie aperture record file.

The viewer executable is bundled inside the pymovie package (``pymovie/bin/``)
at build time by ``scripts/build-exe.ps1``, so it is installed wherever PyMovie
is installed and never has to be located by the user.
"""
import pathlib
import subprocess
import sys
from typing import Optional

VIEWER_NAME = 'PymovieLcReader.exe' if sys.platform == 'win32' else 'PymovieLcReader'
VIEWER_PATH = pathlib.Path(__file__).parent / 'bin' / VIEWER_NAME


def find_viewer() -> Optional[pathlib.Path]:
    """Return the bundled viewer's path, or None if this install doesn't include it."""
    return VIEWER_PATH if VIEWER_PATH.is_file() else None


def open_in_viewer(pymovie_file: pathlib.Path, viewer: pathlib.Path) -> None:
    """Start ``viewer`` with ``pymovie_file`` as its argument, without waiting for it to exit."""
    subprocess.Popen([str(viewer), str(pathlib.Path(pymovie_file).resolve())])
