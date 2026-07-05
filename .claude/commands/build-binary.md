---
description: Build the standalone gridfill executable with PyInstaller
---

Build the standalone `gridfill` executable following the process documented in
[DEVELOPMENT.md](../../DEVELOPMENT.md) ("Standalone executable").

## Steps

1. **Check tkinter is available on the system Python.** The build must use the
   system Python, not uv's managed one (see the note in step 3). Run:

   ```bash
   python3 -c "import tkinter"
   ```

   If this fails, stop and tell the user to install their distro's
   `python3-tkinter` / `python3-tk` package — without it the build will
   produce a crashing executable.

2. **Sync the build dependencies:**

   ```bash
   UV_NO_MANAGED_PYTHON=1 uv sync --extra build
   ```

3. **Run PyInstaller against the spec:**

   ```bash
   UV_NO_MANAGED_PYTHON=1 uv run pyinstaller --noconfirm --clean packaging/gridfill.spec
   ```

   `UV_NO_MANAGED_PYTHON=1` forces uv to use the system Python. On Linux this
   matters: uv's managed (python-build-standalone) builds bundle a Tcl/Tk that
   PyInstaller can't freeze cleanly, producing an executable that crashes on
   startup with `undefined symbol: TclBN_mp_to_ubin`.

4. **Confirm the output.** The executable lands at `dist/gridfill` (or
   `dist/gridfill.exe` on Windows). Verify it exists and report its path and
   size.


## Notes

- If a step fails, stop and report the exact command output rather than
  retrying with different flags.
- This is a build, not a release — it does not tag or push anything. Use
  `/make-release` for cutting a release.
