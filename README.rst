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

AVI codecs
----------

If OpenCV cannot decode an AVI, PyMovie tries its packed RV24 reader and then
PyAV/FFmpeg. Install PyAV in the environment created by uv to enable that
second fallback::

    uv pip install av

The reader regression tests create short RV24 and lossless FFV1 videos in
temporary directories. Run all of them with::

    uv run --with av python -m unittest discover -s tests -v
ADV/AAV on Apple Silicon
------------------------

Adv2 1.2.0 bundles an Intel-only macOS library. After installing the Python
dependencies, Apple Silicon users can build the native reader with::

    uv run python scripts/build_advcore_macos.py

This requires Git and Xcode Command Line Tools (``xcode-select --install``).
The script builds the official ADVCore source at a pinned revision for ARM64,
keeps a backup of the original library, and installs it in the active Python
environment. Repeat this step after reinstalling Adv2.
Tests
-----

Run the OCR pickle compatibility regression tests from the repository root::

    uv run python -m unittest discover -s tests -v

The tests cover NumPy 1.x and 2.x array module paths, corrupted input, and
loading OCR templates from the observation folder or application folder.
Fixtures are generated in temporary directories; existing OCR files are not
modified.

Troubleshooting
---------------

* **"uv: command not found"** — close and reopen your terminal, or follow the
  PATH instructions printed by the uv installer.
* **Windows SmartScreen warning on the uv installer** — click *More info* →
  *Run anyway*. The installer is published by Astral.
* **Corporate proxy / firewall issues** — uv honours standard ``HTTPS_PROXY``
  and ``HTTP_PROXY`` environment variables.

