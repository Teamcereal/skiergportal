# Legacy local data directory

This folder is intentionally empty in the GitHub version of the project. New launcher and packaged-app runs use `%LOCALAPPDATA%/SkiErgPortal/Data` so training data survives application upgrades.

On first launch, the GUI launcher copies existing files here to the persistent user data directory. Direct `uv run streamlit` development starts still use this folder unless `SKIERGPORTAL_DATA_DIR` is set. Files here are ignored by Git.

For a direct development run, load training history by either:

- place Concept2 Logbook CSV exports named `concept2-season-YYYY.csv` in this folder and choose CSV as the data source; or
- enter your personal read-only Concept2 access token in the launcher or set `CONCEPT2_ACCESS_TOKEN` before starting the app.

Never commit CSV exports, API caches, tokens, or other files containing personal training data.