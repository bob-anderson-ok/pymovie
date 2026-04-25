"""PyOTE handoff: launch an installed PyOTE build with a CSV pre-loaded.

PyOTE ships as a single PyApp `.exe` that writes a rendezvous file on every
start. PyMovie reads that file to find a launchable PyOTE entry point and
invokes it with the CSV path as argv[1]. The contract is documented in
``pymovie-integration.md``.
"""

import pathlib
import subprocess
import sys
from typing import Optional

from platformdirs import user_data_dir

# Must match what PyOTE writes. Do not change without coordinating with PyOTE.
MARKER = pathlib.Path(user_data_dir('PyOTE', 'BobAnderson')) / 'exe-path.txt'


def find_pyote() -> Optional[pathlib.Path]:
    """Return the cached PyOTE entry-point path from the rendezvous marker,
    or None if the marker is missing or its path no longer resolves."""
    if not MARKER.exists():
        return None
    try:
        p = pathlib.Path(MARKER.read_text(encoding='utf-8').strip())
    except OSError:
        return None
    return p if p.exists() else None


def write_marker(pyote_path: pathlib.Path) -> None:
    """Write ``pyote_path`` into the rendezvous marker so future PyMovie runs
    can skip the file picker even if PyOTE itself has not run in between."""
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text(str(pyote_path), encoding='utf-8')


def open_in_pyote(csv_path: pathlib.Path, pyote: pathlib.Path) -> None:
    """Launch ``pyote`` with ``csv_path`` as the pre-loaded file.

    Uses ``Popen`` so PyMovie does not wait for the PyOTE session to end and
    multiple PyOTE windows can coexist.
    """
    csv_abs = str(pathlib.Path(csv_path).resolve())
    if sys.platform == 'darwin' and pyote.suffix == '.app':
        # macOS .app bundles need `open -a` with `--args` for argv passthrough.
        subprocess.Popen(['open', '-a', str(pyote), '--args', csv_abs])
    else:
        subprocess.Popen([str(pyote), csv_abs])
