PyMovie
=======

PyMovie is a simple (hopefully) application for extracting lightcurves from occultation videos.

It is specially designed to be robust in both star tracking and data extraction when the
video has been disturbed by wind-shake.

The name was chosen out of respect and deference to LiMovie, a pioneer application
published many years ago.
This application has fewer 'bells and whistles' than LiMovie and so should be easier
to use for a newbie.


Installing
==========

Windows: download the executable (easiest)
------------------------------------------

Windows users can skip the Python toolchain entirely. Go to the
`latest release <https://github.com/bob-anderson-ok/pymovie/releases/latest>`_
page and download ``PyMovie.exe`` from the *Assets* section. Double-click to
run — no installation, no Python setup required. The executable bundles its
own Python runtime and all dependencies.

The first activation will take extra time because it will be downloading the
proper version of Python and all the other dependencies. Subsequent activations will
only tkae a few seconds.

To update later, just download the newer ``PyMovie.exe`` from the release
page and replace the old one.

If you'd rather run from source (all platforms), follow the uv-based
instructions below.

Installing from source (any platform)
-------------------------------------

PyMovie uses `uv <https://docs.astral.sh/uv/>`_ to manage its Python environment.
You do **not** need Python pre-installed — uv will automatically download the
correct version (3.10) on first run.

Step 1. Install uv (one line, user-scope, no admin rights required).

Windows, in PowerShell::

    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

macOS or Linux, in a terminal::

    curl -LsSf https://astral.sh/uv/install.sh | sh

Close and reopen your terminal afterwards so the new ``uv`` command is on your PATH.

Step 2. Get the PyMovie source. Either clone with git::

    git clone https://github.com/bob-anderson-ok/pymovie.git
    cd pymovie

or download the repository as a ZIP from the GitHub page, unzip it, and ``cd``
into the extracted folder.

Step 3. Launch PyMovie::

    uv run pymovie

On first run, uv downloads Python 3.10 (if not already present), installs the
pinned dependencies from ``uv.lock`` into a local ``.venv`` folder, and opens
the PyMovie window. Subsequent runs are near-instant.

Updating
--------

To pick up a new PyMovie release::

    git pull
    uv run pymovie

uv automatically re-syncs the environment whenever ``uv.lock`` has changed,
so there is nothing else to do.

Troubleshooting
---------------

* **"uv: command not found"** — close and reopen your terminal, or follow the
  PATH instructions printed by the uv installer.
* **Windows SmartScreen warning on the uv installer** — click *More info* →
  *Run anyway*. The installer is published by Astral.
* **Corporate proxy / firewall issues** — uv honours standard ``HTTPS_PROXY``
  and ``HTTP_PROXY`` environment variables.

