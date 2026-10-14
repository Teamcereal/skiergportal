# Local Development

Use the source Streamlit app while implementing changes. This avoids rebuilding the Windows package after every edit and keeps development data separate from normal user data.

## One-time setup

Use Python 3.12 to match the Windows Actions build. Python 3.11 or later is required by the project. Install `uv`, then from the repository root run:

```powershell
cd data\system
uv sync --frozen --group build
```

`uv.lock` is the dependency source of truth. Do not edit it manually.

## Run the portal on Windows

In PowerShell, from the repository root:

```powershell
cd data\system
$env:SKIERGPORTAL_DATA_DIR = Join-Path $env:TEMP "SkiErgPortal-dev\Data"
uv run --frozen streamlit run treningshistorikk_app/app.py --server.address 127.0.0.1 --server.port 8502
```

Open `http://localhost:8502`. Streamlit watches the app source and reruns it after Python edits. Stop the server with `Ctrl+C`.

## Run in Codespaces

In the Codespaces terminal:

```bash
cd data/system
uv sync --frozen --group build
export SKIERGPORTAL_DATA_DIR="${TMPDIR:-/tmp}/skiergportal-dev/Data"
uv run --frozen streamlit run treningshistorikk_app/app.py --server.address 0.0.0.0 --server.port 8502
```

Open port `8502` from the VS Code **Ports** view. Streamlit hot reload works the same way as on Windows. Keep the terminal running while testing; use `Ctrl+C` to stop the server.

## Test data and credentials

- `SKIERGPORTAL_DATA_DIR` redirects the app's data reads/writes to a disposable development folder. Use copies of CSV files, never the only copy of real training data.
- The Windows GUI launcher uses `%LOCALAPPDATA%\SkiErgPortal\Data`. If you test the source launcher, set `LOCALAPPDATA` to a temporary profile first, as shown below.
- Do not commit CSV files, tokens, `.streamlit/secrets.toml`, or test output. Use a dedicated read-only Concept2 test token only when API behavior is part of the change.
- The first public stable release may not exist during development. In that case, the update check can report that it could not find a release; this must not block the portal from starting.

## Test the Windows GUI launcher

This requires Windows with Tkinter. From PowerShell at the repository root:

```powershell
cd data\system
uv sync --frozen --group build
$env:LOCALAPPDATA = Join-Path $env:TEMP "SkiErgPortal-launcher-dev-profile"
uv run --frozen python Start-Treningshistorikk-GUI.pyw
```

This starts the source launcher and its development Streamlit server on port `8501`. The temporary `LOCALAPPDATA` keeps its token and data operations out of the normal user profile. Restart the launcher after editing Tkinter code; Streamlit source changes reload in the browser.

## Focused checks before pushing

Run from `data/system`:

```powershell
uv run --frozen python -m unittest discover -s . -p "test_*update*.py"
uv run --frozen python -m py_compile Start-Treningshistorikk-GUI.pyw release_updates.py app_update_helper.py skiergportal_version.py
```

Then review the changed files and use a feature branch and pull request. A source-mode run does not validate the frozen Windows package, updater process replacement, or Windows-specific file locking; the Windows Actions build and a real Windows acceptance test remain required before release.

## Recommended edit/test loop

1. Create or switch to a feature branch; do not develop directly on `main`.
2. Start the source Streamlit app with the isolated data directory above.
3. Make a small change and validate it in the browser after Streamlit reloads.
4. Run the focused unit tests and inspect the app log if behavior differs.
5. Commit and push the branch, open/update the PR, and run **Windows build** on that exact branch and commit.
6. Merge only after review and Windows checks pass. Publish a version tag only when intentionally creating a release.