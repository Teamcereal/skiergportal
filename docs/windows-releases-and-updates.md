# Windows Releases and One-Click Updates

# App Releases, Updates, and iOS Roadmap

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

#### Windows test before merging the release PR

- [ ] In Actions, run `Windows build` on the PR branch. Confirm the run's branch and head SHA match the latest PR commit, and that build, updater tests, smoke test, ZIP packaging, and artifact upload all pass.
- [ ] Download the run artifact `SkiErgPortal-windows-x64` and extract the artifact bundle. It contains the app package `SkiErgPortal-windows-x64.zip` and `SkiErgPortal-windows-x64.zip.sha256`.
- [ ] Verify the app ZIP before extracting it:

```powershell
$expected = (Get-Content .\SkiErgPortal-windows-x64.zip.sha256 -Raw).Trim().Split()[0]
$actual = (Get-FileHash .\SkiErgPortal-windows-x64.zip -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expected) { throw "SHA-256 mismatch" }
```

- [ ] Extract the app ZIP to a writable test folder such as `%LOCALAPPDATA%\Programs\SkiErgPortal`. Do not extract it into `%LOCALAPPDATA%\SkiErgPortal`, which is reserved for user data, and do not move the EXE out of the package.
- [ ] Test on a separate Windows 10/11 x64 machine or a clean Windows user profile. The app should run without separately installing Python or uv and without administrator privileges.
- [ ] Start `SkiErgPortal.exe`. Confirm the launcher opens, **Start** starts Streamlit, the browser reaches `http://localhost:8501`, and the main page renders without a server startup error.
- [ ] Exercise the views and workflows changed by the PR using a copy of test CSV data. Confirm charts, filters, and relevant controls behave as expected; do not use the only copy of real training data.
- [ ] Confirm files created by the app are under `%LOCALAPPDATA%\SkiErgPortal\Data`, not inside the extracted application folder. Close and reopen the app and confirm the test data/settings persist.
- [ ] Exercise **Stop**, close the launcher, and start it again. Confirm there is no stale Streamlit process or port conflict.
- [ ] Disable network access temporarily and launch the app. The portal must remain usable even if update checking fails; restore network access afterwards.
- [ ] Record the Windows version, tested commit SHA, workflow run URL, checksum result, test data used, and any error/log output before marking the PR ready.

Before the first stable GitHub Release exists, the update check has no stable version to compare against. A non-blocking "could not check" state is expected; it must not prevent the current app from starting. Do not treat an Actions artifact as a published release.

#### Update installation test before broad distribution

- [ ] Test a current-version result and an offline update check.
- [ ] Test a real upgrade from an older version using a controlled staging release or a dedicated test repository; do not publish a fake stable version to the public release channel just to test.
- [ ] Confirm the updater reports progress, closes the launcher/server, installs the new version, and relaunches it.
- [ ] Confirm CSV files, settings, tokens, and other user data remain unchanged after the upgrade.
- [ ] Test a wrong checksum, invalid ZIP, interrupted download, missing file, and failed new-version smoke test. Each case must keep the previous app usable and provide an actionable error.
- [ ] Publish the first public stable release only after the Windows package and the update path have passed their applicable tests.

#### Release acceptance criteria

- [ ] A user can download one ZIP from GitHub Releases and run `SkiErgPortal.exe` from the extracted application folder.
- [ ] The launcher identifies a newer stable release and offers a clearly labeled, user-confirmed update.
- [ ] A successful update replaces the application, restarts it, and preserves all user data.
- [ ] Failed or invalid updates leave the previous application usable and provide an actionable error.
- [ ] The release workflow publishes nothing unless tag validation, build, package checks, and runtime smoke tests all pass.

## iOS roadmap (planning only)

No iOS build is part of the current Windows release/update implementation. The existing Tkinter launcher, Streamlit runtime, and PyInstaller Windows bundle cannot be turned directly into an iOS `.ipa`; iOS needs a different application/runtime and distribution path.

#### 0. Requirements and architecture decision

- [ ] Decide whether iOS means a mobile website/PWA opened in Safari or a native iPhone app distributed through TestFlight/App Store.
- [ ] Define required offline behavior, CSV import/export, Concept2 API access, token handling, comments/settings, and whether data must stay only on the user's device.
- [ ] Compare a hosted mobile web app (more reuse of Streamlit, but requires an HTTPS service, authentication, and an explicit server-side data policy) with a native SwiftUI client (better iOS integration, but requires a backend/API or a deliberate port of app logic).
- [ ] Reject a direct Tkinter/PyInstaller-to-iOS packaging assumption; test any alternative Python UI framework in a small throwaway spike before committing to it.
- [ ] Write down the chosen architecture, data flows, threat model, hosting costs, and expected maintenance before implementation.

#### 1. Build and distribution preparation

- [ ] Identify required Apple hardware/tooling: macOS with Xcode, signing identities, provisioning profiles, and an Apple Developer account for TestFlight/App Store distribution.
- [ ] Define secure token storage (Keychain for native), user consent, data deletion/export, and privacy disclosures before connecting Concept2 accounts.
- [ ] Decide how to reuse or port calculations and how a client talks to any service; add API contracts and versioning before UI implementation.
- [ ] Design iPhone-sized layouts and accessibility states for loading, empty data, offline, API errors, and token expiry.
- [ ] Add iOS unit/UI tests and a macOS CI lane only after the architecture is approved.

#### 2. Device validation and release

- [ ] Test on supported physical iPhone/iOS versions, including CSV file import, secure token handling, accessibility, offline behavior, and data persistence.
- [ ] Validate App Store privacy declarations, signing, TestFlight feedback, upgrade behavior, and recovery from failed releases.
- [ ] Publish an iOS build only after product, privacy, architecture, device-test, and distribution checks are approved.

The next iOS action is requirements/architecture discovery only. Do not add an iOS build job or change the current Windows release flow until those decisions are recorded.

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