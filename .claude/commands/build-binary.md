---
description: Build the standalone gridfill executable with PyInstaller
---

Build the standalone `gridfill` executable following the process documented in
[DEVELOPMENT.md](../../DEVELOPMENT.md) ("Standalone executable").

All commands run from the `python/` directory (the Python project root).

## Steps

1. **Sync the build dependencies:**

   ```bash
   cd python && uv sync --extra build
   ```

2. **Run PyInstaller against the spec:**

   ```bash
   uv run pyinstaller --noconfirm --clean packaging/gridfill.spec
   ```

3. **Confirm the output.** The executable lands at `python/dist/gridfill` (or
   `python/dist/gridfill.exe` on Windows). Verify it exists and report its path
   and size.


## Notes

- If a step fails, stop and report the exact command output rather than
  retrying with different flags.
- This is a build, not a release — it does not tag or push anything. Use
  `/make-release` for cutting a release.
