# build-exe.ps1 — produce a single PyMovie.exe via PyApp.
#
# Prerequisites (one-time on the build machine):
#   1. uv              — already installed as part of normal PyMovie development.
#   2. Rust toolchain  — install with:  winget install Rustlang.Rustup
#                                       (or download rustup-init.exe from https://rustup.rs)
#      After install, close and reopen PowerShell so `cargo` is on PATH.
#
# Usage (from the project root):
#   powershell -ExecutionPolicy Bypass -File scripts\build-exe.ps1
#
# Output:  dist\PyMovie.exe

$ErrorActionPreference = "Stop"
Set-Location -Path (Join-Path $PSScriptRoot "..")

Write-Host "==> Building PyMovie wheel with uv..."
uv build
if ($LASTEXITCODE -ne 0) { throw "uv build failed" }

$wheel = Get-ChildItem -Path dist -Filter "pymovie-*-py3-none-any.whl" |
         Sort-Object LastWriteTime -Descending |
         Select-Object -First 1
if (-not $wheel) { throw "no pymovie wheel found in dist/" }
Write-Host "    wheel: $($wheel.FullName)"

Write-Host "==> Configuring PyApp..."
$env:PYAPP_PROJECT_PATH       = $wheel.FullName
$env:PYAPP_EXEC_SPEC          = "pymovie.main:main"
$env:PYAPP_IS_GUI             = "true"
$env:PYAPP_PYTHON_VERSION     = "3.10"
$env:PYAPP_UV_ENABLED         = "true"
$env:PYAPP_DISTRIBUTION_EMBED = "true"

# Tell rustc to use the self-contained MinGW bundle shipped with rustup's
# `rust-mingw` component (rust-lld + bundled libgcc_eh.a / crt*.o). This
# avoids the system gcc linker looking for libgcc_eh.a that TDM-GCC 10.3.0
# does not ship.
$env:RUSTFLAGS = "-C link-self-contained=yes"
Remove-Item Env:CC -ErrorAction SilentlyContinue

# rustc invokes dlltool.exe directly (not via the linker), and picks up the
# first one on PATH. An older 32-bit MinGW installed at C:\MinGW\bin errors
# out on 64-bit targets, so put TDM-GCC-64's 64-bit dlltool ahead of it.
$env:PATH = "C:\TDM-GCC-64\bin;$env:PATH"

Write-Host "==> Building PyApp binary with cargo (this can take several minutes on first build)..."
# Use rustup's stable-x86_64-pc-windows-gnu toolchain, which ships its own
# matched MinGW (`rust-mingw` component) providing the correct dlltool.exe
# and libgcc_eh.a. This avoids incompatibilities with older system GCC
# installs like TDM-GCC 10.3.0.
cargo +stable-x86_64-pc-windows-gnu install pyapp --force --root (Join-Path $PWD "target\pyapp")
if ($LASTEXITCODE -ne 0) { throw "cargo install pyapp failed" }

$src = Join-Path $PWD "target\pyapp\bin\pyapp.exe"
$dst = Join-Path $PWD "dist\PyMovie.exe"
if (-not (Test-Path $src)) { throw "expected output not found: $src" }
if (Test-Path $dst) { Remove-Item $dst }
Move-Item -Path $src -Destination $dst

$size = (Get-Item $dst).Length / 1MB
Write-Host ""
Write-Host "==> Done. Output: $dst  ($([math]::Round($size, 1)) MB)"
Write-Host "    Test on a clean Windows machine before distributing."
