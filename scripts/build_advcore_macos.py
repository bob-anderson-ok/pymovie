"""Build the native ADV reader for the active Apple Silicon Python environment."""

import importlib.util
import platform
from pathlib import Path
import shutil
import subprocess
import tempfile


REVISION = "bbcda85214540c2e8996b7715887c358f68141cd"
SOURCE = "https://github.com/AstroDigitalVideo/ADVCore.git"


def main():
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise SystemExit("Run this script with native ARM64 Python on macOS.")
    spec = importlib.util.find_spec("Adv2")
    if spec is None:
        raise SystemExit("Install the project dependencies in this environment first.")
    target = Path(spec.origin).parent / "Adv2DLLlibs" / "libAdvCore.dylib"
    for tool in ("git", "clang", "clang++"):
        if shutil.which(tool) is None:
            raise SystemExit(f"Missing {tool}; install Xcode Command Line Tools.")

    with tempfile.TemporaryDirectory(prefix="pymovie-advcore-") as temporary:
        root = Path(temporary)
        source = root / "source"
        subprocess.run(["git", "clone", SOURCE, str(source)], check=True)
        subprocess.run(["git", "checkout", "--detach", REVISION], cwd=source, check=True)
        src = source / "src"
        obj = root / "quicklz.o"
        output = root / "libAdvCore.dylib"
        subprocess.run([
            "clang", "-O2", "-fPIC", "-c", str(src / "quicklz.c"), "-o", str(obj)
        ], check=True)
        subprocess.run([
            "clang++", "-std=c++11", "-O2", "-fPIC", "-dynamiclib",
            *map(str, sorted(src.glob("*.cpp"))), str(obj), "-o", str(output)
        ], check=True)
        backup = target.with_suffix(".original.dylib")
        if not backup.exists():
            shutil.copy2(target, backup)
        shutil.copy2(output, target)
        print(f"Installed ARM64 ADV library: {target}")


if __name__ == "__main__":
    main()
