# Windows Releases and One-Click Updates

## Goal

Make SkiErgPortal straightforward to download and keep current without changing the existing training-data format, calculations, or Streamlit application behavior.

The first public release should include update checking. A release without an updater cannot notify users who already installed it; those users would need to download a later version manually once.

## Current Packaging

- The Windows workflow builds a PyInstaller `--onedir` application and smoke-tests the launcher, Streamlit CLI, and HTTP health endpoint.
- The runnable application is the complete `SkiErgPortal` directory, not `SkiErgPortal.exe` by itself.
- User data is stored separately at `%LOCALAPPDATA%\SkiErgPortal\Data` and must never be replaced or removed by an application update.
- Manual workflow runs upload an Actions artifact retained for 14 days. Version-tagged builds publish the ZIP as a durable GitHub Release asset.

## Recommended Design

Keep the application as a portable folder. Users extract the complete release ZIP into a writable folder such as `%LOCALAPPDATA%\Programs\SkiErgPortal` and run `SkiErgPortal.exe` from there. Do not install it inside `%LOCALAPPDATA%\SkiErgPortal`, which contains user data. Updates replace application files in the install folder while leaving `%LOCALAPPDATA%\SkiErgPortal\Data` untouched.

The launcher checks GitHub Releases for a newer stable version without delaying normal startup. When one is available, it presents an **Update available** action in the launcher. No update is downloaded or installed until the user confirms.

An updater process separate from the running GUI and Streamlit server performs the replacement. Windows can lock executables while they are running, so the launcher must stop the server and exit before the updater swaps files. The updater stages and validates the full package, keeps a rollback copy until the new version starts, then relaunches the application.

## Implementation Plan

### 1. Define versioning and release assets

- [x] Use semantic versions and Git tags such as `v1.0.0`; do not reuse or move published tags.
- [x] Keep the application version in one small, explicit source of truth that is included in the package.
- [x] Name the release ZIP consistently, for example `SkiErgPortal-windows-x64.zip`.
- [x] Package the complete `dist/SkiErgPortal` directory, including the GUI, Streamlit server, app files, and required resources.
- [x] Generate a SHA-256 checksum alongside the ZIP.

### 2. Automate GitHub Releases

- [x] Retain the current Windows build and smoke tests as required gates.
- [x] Keep manual workflow runs available for testing and Actions artifacts.
- [x] Add a release path triggered by a version tag. It must build on Windows, pass all smoke tests, create the ZIP and checksum, then attach both to a GitHub Release.
- [x] Scope write permission to the release-publishing job only. A failed build must never publish a release.
- [x] Include concise release notes describing user-visible changes and compatibility.

### 3. Add update discovery to the launcher

- [x] Query the official `Teamcereal/skiergportal` Releases endpoint over HTTPS and compare the latest stable tag to the packaged version.
- [x] Perform the network request off the Tkinter UI thread, with a short timeout. Offline access, API errors, or rate limits must not prevent the current app from starting.
- [x] Show clear states: checking, up to date, update available, and check failed. Offer a manual **Check for updates** action as well as the update button when a newer version is found.
- [x] Display the target version and release notes before confirmation. Never install silently.

### 4. Implement the updater

- [x] Download only the expected ZIP asset from the official repository's release; reject unexpected hosts, asset names, or versions.
- [x] Verify the downloaded SHA-256 checksum before extracting anything.
- [x] Extract into a fresh staging directory and reject archive entries that could escape that directory (zip-slip/path traversal).
- [x] Confirm that expected files, including `SkiErgPortal.exe`, `streamlit_server/streamlit_server.exe`, `streamlit_server/app/app.py`, and Streamlit static resources, exist in staging.
- [x] Start a separate updater helper, stop the Streamlit child process and launcher cleanly, and replace application files only after validation succeeds.
- [x] Preserve the separate user-data directory. Keep a rollback copy until the new version starts successfully; restore it if replacement or launch fails.
- [x] Show download/install progress and a useful error with a retry path. Do not delete the old application before the staged package is verified.

### 5. Verify before public launch

- [ ] Test a clean install from the release ZIP on a Windows machine.
- [ ] Test an upgrade from the previous version while retaining CSV files, settings, tokens, and other user data.
- [ ] Test that a current version reports up to date and an offline check leaves the app usable.
- [ ] Test that a wrong checksum, invalid ZIP, interrupted download, or failed replacement does not damage the installed app or user data.
- [ ] Test that the updater can replace files while the GUI and Streamlit server are running, then relaunches the new version.
- [ ] Publish the first public release only after the release ZIP has passed these tests.

## Security and Operational Rules

- Releases are explicit and user-confirmed; never execute an update from an arbitrary URL or install an unverified archive.
- Checksums detect corruption, but are not a substitute for code signing against a compromised release account. Consider Windows code signing before broad distribution to reduce SmartScreen warnings and strengthen publisher identity.
- The portable install folder must be writable by the current user. If it is not, explain that the user must move/reinstall the app to a writable location; do not request administrator rights silently.
- Keep build artifacts and public release assets distinct. Actions artifacts are temporary CI outputs; Releases are the stable download channel.
- Continue to test changes through branches and pull requests. Publishing a release is a separate, deliberate versioned step.

## Acceptance Criteria

- [ ] A user can download one ZIP from the GitHub Releases page and run the app by launching `SkiErgPortal.exe` from the extracted folder.
- [ ] The launcher identifies a newer stable release and offers a clearly labeled, user-confirmed update.
- [ ] A successful update replaces the complete application, restarts it, and preserves all user data.
- [ ] Failed or invalid updates leave the previous application usable and provide an actionable error.
- [ ] The Windows release workflow publishes nothing unless build, packaging checks, and runtime smoke tests all pass.